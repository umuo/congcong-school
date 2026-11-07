"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api/client";
import {
  Field,
  FloatingToast,
  InfoPopover,
  ModalDialog,
  type ToastTone,
} from "./AccountShell";
import type { Student } from "./StudentForm";

type Book = {
  id: string;
  subject_code: string;
  title: string;
  grade: number;
  school_system: string;
  publisher_label: string | null;
  edition_label: string | null;
  publication_year: number | null;
  isbn: string | null;
  units: { number: number; title: string }[];
};
type Choice = {
  subject_code: string;
  enabled: boolean;
  book_id: string | null;
  current_unit_number: number | null;
};
type Curriculum = {
  revision: number;
  subjects: Choice[];
  history: {
    id: string;
    subject_code: string;
    book_id: string;
    started_at: string;
    ended_at: string | null;
    snapshot: { title?: string };
  }[];
};

export function CurriculumForm({
  student,
  onSave,
}: {
  student: Student;
  onSave: () => void;
}) {
  const [subjects, setSubjects] = useState<{ code: string; name: string }[]>(
    [],
  );
  const [books, setBooks] = useState<Book[]>([]);
  const [saved, setSaved] = useState<Curriculum | null>(null);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [allGrades, setAllGrades] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; tone: ToastTone }>({
    text: "",
    tone: "info",
  });
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      api<Curriculum>(`/students/${student.id}/curriculum`, {
        signal: controller.signal,
      }),
      api<{ items: Book[] }>("/textbooks", { signal: controller.signal }),
      api<{ code: string; name: string }[]>("/subjects", {
        signal: controller.signal,
      }),
    ])
      .then(([c, b, s]) => {
        setSaved(c);
        setBooks(b.items);
        setSubjects(s);
        setChoices(
          Object.fromEntries(c.subjects.map((v) => [v.subject_code, v])),
        );
      })
      .catch((e: Error) => {
        if (!controller.signal.aborted) {
          setToast({ text: e.message, tone: "error" });
        }
      });
    return () => controller.abort();
  }, [student.id]);

  function change(code: string, value: Partial<Choice>) {
    setChoices((old) => ({
      ...old,
      [code]: {
        ...(old[code] ?? {
          subject_code: code,
          enabled: false,
          book_id: null,
          current_unit_number: null,
        }),
        ...value,
      },
    }));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!saved) return;
    setBusy(true);
    setToast({ text: "", tone: "info" });
    try {
      const result = await api<Curriculum>(
        `/students/${student.id}/curriculum`,
        {
          method: "PUT",
          headers: { "If-Match": String(saved.revision) },
          body: JSON.stringify({ subjects: Object.values(choices) }),
        },
      );
      setSaved(result);
      setToast({
        text: "教材配置已保存，原有选书历史会继续保留。",
        tone: "success",
      });
      onSave();
    } catch (e) {
      setToast({
        text: e instanceof Error ? e.message : "保存失败",
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="account-card">
      <FloatingToast
        message={toast.text}
        tone={toast.tone}
        onDismiss={() => setToast({ text: "", tone: "info" })}
      />

      <div className="account-section-head">
        <div className="account-section-title-group">
          <h2>{student.nickname}的教材配置</h2>
          <InfoPopover label="选书说明" title="教材绑定与历史记录说明">
            <p>
              当前没有已核实的地区自动推荐，请对照孩子实际使用的纸质课本手动选择。
            </p>
            <p>
              不同学科可选不同出版社版本；换书、停用学科和升年级均会完整保留原有选书历史与作答记录。
            </p>
          </InfoPopover>
        </div>
        <div className="account-actions">
          <label className="account-toggle-label">
            <input
              type="checkbox"
              checked={allGrades}
              onChange={(e) => setAllGrades(e.target.checked)}
            />
            显示全部年级教材（默认显示 {student.grade} 年级）
          </label>
          <button
            type="button"
            className="secondary"
            onClick={() => setHistoryOpen(true)}
          >
            选书历史（{saved?.history.length ?? 0}）
          </button>
        </div>
      </div>

      {saved ? (
        <form onSubmit={save}>
          <div className="curriculum-subject-grid">
            {subjects.map((subject) => {
              const choice = choices[subject.code];
              const book = books.find((b) => b.id === choice?.book_id);
              const options = books.filter(
                (b) =>
                  b.subject_code === subject.code &&
                  (allGrades ||
                    b.grade === student.grade ||
                    b.id === choice?.book_id),
              );
              const isEnabled = choice?.enabled ?? false;
              return (
                <fieldset
                  key={subject.code}
                  className={`curriculum-subject-card${isEnabled ? "" : " is-disabled"}`}
                >
                  <div className="curriculum-subject-card-head">
                    <strong>{subject.name}</strong>
                    <label className="account-toggle-label">
                      <input
                        type="checkbox"
                        checked={isEnabled}
                        disabled={!!student.archived_at}
                        onChange={(e) =>
                          change(subject.code, { enabled: e.target.checked })
                        }
                      />
                      启用{subject.name}
                    </label>
                  </div>
                  <Field label={`${subject.name}教材`}>
                    <select
                      value={choice?.book_id ?? ""}
                      disabled={!!student.archived_at}
                      onChange={(e) =>
                        change(subject.code, {
                          book_id: e.target.value || null,
                          current_unit_number: null,
                        })
                      }
                    >
                      <option
                        value=""
                        disabled={
                          !!saved.subjects.find(
                            (s) => s.subject_code === subject.code,
                          )?.book_id
                        }
                      >
                        尚未选择教材
                      </option>
                      {options.map((b) => (
                        <option value={b.id} key={b.id}>
                          {b.title} · {b.publisher_label ?? "出版社未知"} ·{" "}
                          {b.edition_label ?? "版次未知"} · {b.school_system} ·{" "}
                          {b.id}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {book ? (
                    <>
                      <small>
                        出版年份：{book.publication_year ?? "未知"} · ISBN：
                        {book.isbn ?? "未知"}
                      </small>
                      <Field label={`${subject.name}当前单元`}>
                        <select
                          value={choice?.current_unit_number ?? ""}
                          disabled={!!student.archived_at}
                          onChange={(e) =>
                            change(subject.code, {
                              current_unit_number: e.target.value
                                ? Number(e.target.value)
                                : null,
                            })
                          }
                        >
                          <option value="">暂不指定</option>
                          {book.units.map((u) => (
                            <option key={u.number} value={u.number}>
                              {u.number}. {u.title}
                            </option>
                          ))}
                        </select>
                      </Field>
                    </>
                  ) : null}
                </fieldset>
              );
            })}
          </div>
          <div className="account-actions">
            <button disabled={busy || !!student.archived_at}>
              保存教材配置
            </button>
          </div>
        </form>
      ) : (
        <p role="status">正在读取教材目录…</p>
      )}

      <ModalDialog
        open={historyOpen}
        title={`${student.nickname}的选书历史`}
        subtitle={`共记录 ${saved?.history.length ?? 0} 次教材绑定`}
        onClose={() => setHistoryOpen(false)}
      >
        {!saved?.history.length ? (
          <p>暂无教材绑定历史记录。</p>
        ) : (
          <div className="account-list">
            {saved.history.map((h) => (
              <div className="account-row" key={h.id}>
                <div>
                  <strong>{h.snapshot.title ?? h.book_id}</strong>
                  <small>
                    {h.book_id} · {h.ended_at ? "历史选择" : "当前选择"} ·{" "}
                    {new Date(h.started_at).toLocaleDateString("zh-CN")}
                  </small>
                </div>
              </div>
            ))}
          </div>
        )}
      </ModalDialog>
    </section>
  );
}
