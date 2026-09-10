import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from backend.api.auth import get_current_user
from backend.models.schemas import AnalysisResponse, HistoryEntry

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix='/api/v1', tags=['Analysis'])


@router.post(
    '/analyze-resume',
    response_model=AnalysisResponse,
    summary='Analyze a resume, optionally against a job description',
)
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(..., description='Resume file — PDF or DOCX, max 5 MB'),
    job_description: str = Form('', description='Job description text (optional)'),
    user_id: str = Depends(get_current_user),
) -> AnalysisResponse:
    from backend.services.resume_parser import FileParsingError, FileValidationError, parse_resume_file

    nlp = request.app.state.nlp
    embedder = request.app.state.embedder

    filename = resume.filename or 'resume'
    file_bytes = await resume.read()

    # ---- Parse the uploaded file into plain text -------------------------
    try:
        resume_text, _metadata = parse_resume_file(file_bytes, filename)
    except (FileValidationError, FileParsingError) as exc:
        # These carry messages written for the end user — pass them straight through.
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception(f'Unexpected parse failure for {filename!r}')
        raise HTTPException(status_code=422, detail=f'Could not read the resume: {exc}')

    logger.info(f'Parsed {filename!r}: {len(resume_text)} chars extracted')

    # ---- Run the analysis pipeline ---------------------------------------
    try:
        from backend.services.resume_analyzer import analyze_full_resume

        result = analyze_full_resume(
            resume_text=resume_text,
            nlp=nlp,
            embedder=embedder,
            job_description=job_description,
        )
    except Exception as exc:
        logger.exception('Analysis pipeline failed')
        raise HTTPException(status_code=500, detail=f'Analysis failed: {exc}')

    response = AnalysisResponse(
        **result,
        filename=filename,
        analyzed_at=datetime.now(timezone.utc),
    )

    # History is a convenience, not part of the result — never fail the
    # request because the database is unreachable.
    try:
        from backend.database.supabase_db import save_analysis

        await save_analysis(user_id, response)
    except Exception as exc:
        logger.warning(f'History save failed (non-blocking): {exc}')

    return response


@router.get('/health', summary='Liveness + model readiness')
async def health_check(request: Request) -> dict:
    return {
        'status': 'healthy',
        'nlp_loaded': getattr(request.app.state, 'nlp', None) is not None,
        'embedder_loaded': getattr(request.app.state, 'embedder', None) is not None,
    }


@router.get('/history', response_model=list[HistoryEntry], summary="List the caller's past analyses")
async def get_history(user_id: str = Depends(get_current_user)) -> list[HistoryEntry]:
    from backend.database.supabase_db import get_user_history

    try:
        return await get_user_history(user_id)
    except Exception as exc:
        logger.exception('History fetch failed')
        raise HTTPException(status_code=500, detail=f'Could not load history: {exc}')


@router.delete('/history/{analysis_id}', summary='Delete one saved analysis')
async def delete_history_entry(analysis_id: str, user_id: str = Depends(get_current_user)) -> dict:
    from backend.database.supabase_db import delete_analysis

    try:
        deleted = await delete_analysis(analysis_id, user_id)
    except Exception as exc:
        logger.exception(f'History delete failed for {analysis_id}')
        raise HTTPException(status_code=500, detail=f'Could not delete: {exc}')

    if not deleted:
        raise HTTPException(status_code=404, detail='Analysis not found.')
    return {'status': 'deleted', 'id': analysis_id}


def _pdf_response(analysis: dict, filename: str) -> Response:
    from backend.services.pdf_export import generate_combined_pdf
    from backend.services.report_generator import generate_html_reports

    html_docs = generate_html_reports(analysis)
    pdf_bytes = generate_combined_pdf(html_docs)
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@router.post('/reports/pdf', summary='Render an analysis payload as a PDF report')
async def generate_pdf(data: AnalysisResponse, user_id: str = Depends(get_current_user)) -> Response:
    from backend.services.pdf_export import PdfUnavailableError

    try:
        return _pdf_response(data.model_dump(mode='json'), 'ats-report.pdf')
    except PdfUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception('PDF generation failed')
        raise HTTPException(status_code=500, detail=f'Could not generate PDF: {exc}')


@router.get('/history/{analysis_id}/pdf', summary='PDF report for a saved analysis')
async def generate_history_pdf(analysis_id: str, user_id: str = Depends(get_current_user)) -> Response:
    from backend.database.supabase_db import get_analysis
    from backend.services.pdf_export import PdfUnavailableError

    entry = await get_analysis(analysis_id, user_id)
    if entry is None or not entry.analysis:
        raise HTTPException(status_code=404, detail='Analysis not found.')

    try:
        return _pdf_response(entry.analysis, f'ats-report-{analysis_id}.pdf')
    except PdfUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception(f'PDF generation failed for {analysis_id}')
        raise HTTPException(status_code=500, detail=f'Could not generate PDF: {exc}')
