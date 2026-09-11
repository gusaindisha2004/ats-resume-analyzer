import Link from "next/link";
import { BadgeCheck, FileSearch, Target } from "lucide-react";
import { Card, CardBody } from "@/components/ui/card";

const FEATURES = [
  {
    icon: BadgeCheck,
    title: "Skill validation",
    body: "Anyone can list Kubernetes. This checks every claimed skill against your actual projects and experience bullets using sentence embeddings, then shows you which ones you can't back up.",
  },
  {
    icon: Target,
    title: "Job description matching",
    body: "Paste a posting and get keyword overlap plus semantic similarity — so you see both the exact terms the filter looks for and whether your resume reads like the role at all.",
  },
  {
    icon: FileSearch,
    title: "Specific, fixable feedback",
    body: "Not 'improve your formatting'. Every issue comes with where it appears, why it costs you, the action items to fix it, and a rewritten example.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="hero-wash pt-8 text-center sm:pt-16">
        <h1 className="mx-auto max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          Find out what an ATS actually sees in your resume
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-pretty text-lg text-muted-foreground">
          Upload a resume, optionally paste the job posting, and get a scored
          breakdown with the specific edits that would move it.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            href="/analyze"
            className="rounded-lg bg-primary px-6 py-3 font-medium text-primary-foreground shadow-sm shadow-primary/25 transition-colors hover:bg-primary-hover"
          >
            Analyze a resume
          </Link>
          <Link
            href="#how"
            className="rounded-lg border border-border bg-surface px-6 py-3 font-medium transition-colors hover:border-primary/30 hover:bg-primary-subtle"
          >
            How it works
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <Card key={title}>
            <CardBody className="space-y-3">
              <Icon className="size-5 text-primary" aria-hidden />
              <h2 className="font-semibold">{title}</h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {body}
              </p>
            </CardBody>
          </Card>
        ))}
      </section>

      <section id="how" className="scroll-mt-20">
        <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
        <ol className="mt-6 space-y-5">
          {[
            [
              "Parse",
              "The file is read with pdfplumber (falling back to PyPDF2), including hyperlinks that plain text extraction drops.",
            ],
            [
              "Extract",
              "A Llama 3.3 model on Groq turns the raw text into structured JSON — skills, experience with durations, projects, action verbs.",
            ],
            [
              "Score",
              "Five components — keywords, content, formatting, skill validation, ATS compatibility — combine into one weighted score out of 100.",
            ],
            [
              "Explain",
              "Rule-based checks turn the structured data into concrete issues, each with fixes and an example rewrite.",
            ],
          ].map(([title, body], i) => (
            <li key={title} className="flex gap-4">
              <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                {i + 1}
              </span>
              <div>
                <h3 className="font-medium">{title}</h3>
                <p className="mt-0.5 text-sm text-muted-foreground">{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
