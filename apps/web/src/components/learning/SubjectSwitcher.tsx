"use client";
import { BookOpen, Calculator, Languages, FlaskConical } from "lucide-react";
import { subjectChoices, type CurriculumSubject } from "@/lib/learning/subjects";

const icons = { chinese: BookOpen, math: Calculator, english: Languages, science: FlaskConical };

export function SubjectSwitcher({ subjects, book, ready, disabled = false, onSelect }: {
  subjects: readonly CurriculumSubject[]; book: string; ready: boolean; disabled?: boolean; onSelect: (book: string) => void;
}) {
  return <nav id="forest-subjects" className="forest-subject-switch" aria-label="切换学科" aria-busy={!ready}>
    {subjectChoices(subjects).map(subject => {
      const Icon = icons[subject.code];
      return <button key={subject.code} type="button" disabled={disabled || !ready || !subject.bookId}
        aria-pressed={Boolean(subject.bookId && subject.bookId === book)}
        aria-label={ready && !subject.bookId ? `${subject.label}，请家长配置` : subject.label}
        onClick={() => { if (ready && !disabled && subject.bookId && subject.bookId !== book) onSelect(subject.bookId); }}>
        <span><Icon size={16} aria-hidden />{subject.label}</span>
        {ready && !subject.bookId ? <small>待配置</small> : null}
      </button>;
    })}
  </nav>;
}
