"use client";
import { useEffect, useRef, useState } from "react";
import {
  api,
  post,
  announceSessionChange,
  type Account,
} from "@/lib/api/client";
import {
  FloatingToast,
  InfoPopover,
  ModalDialog,
  type ToastTone,
} from "./AccountShell";
import type { Student } from "./StudentForm";

type Policy = { retention_days: number; notice: string };
type Preview = {
  preview_id: string;
  source_hash: string;
  revision: number;
  confirmed: boolean;
  report: {
    mapped_lessons: number;
    mapped_mistakes: number;
    unmapped: unknown[];
    conflicts: string[];
    limitations: string[];
  };
};

export function downloadJSON(name: string, value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function PortabilityPanel({
  account,
  student,
  onDeleted,
  onImported,
  embedded = false,
}: {
  account: Account;
  student?: Student;
  onDeleted: () => void;
  onImported: () => void;
  embedded?: boolean;
}) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [toast, setToast] = useState<{ text: string; tone: ToastTone }>({
    text: "",
    tone: "info",
  });
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [exportFile, setExportFile] = useState<{
    href: string;
    name: string;
  } | null>(null);
  const deleteKey = useRef<string | null>(null);

  useEffect(
    () => () => {
      if (exportFile) URL.revokeObjectURL(exportFile.href);
    },
    [exportFile],
  );

  useEffect(() => {
    const controller = new AbortController();
    void api<Policy>("/privacy/policy", { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) setPolicy(value);
      })
      .catch((e: Error) => {
        if (!controller.signal.aborted) {
          setToast({ text: e.message, tone: "error" });
        }
      });
    return () => controller.abort();
  }, []);

  async function upload(file?: File) {
    if (!student || !file) return;
    setToast({ text: "", tone: "info" });
    setPreview(null);
    if (file.size > 5 * 1024 * 1024) {
      setToast({
        text: "单个档案最多 5 MB，请逐档案导入。",
        tone: "error",
      });
      return;
    }
    setBusy(true);
    try {
      const value = await api<Preview>(
        `/students/${student.id}/imports/preview`,
        { method: "POST", body: await file.text() },
      );
      setPreview(value);
    } catch (e) {
      setToast({
        text: e instanceof Error ? e.message : "预览失败",
        tone: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  const name = student?.nickname ?? account.family?.name ?? "";

  const body = (
    <>
      <FloatingToast
        message={toast.text}
        tone={toast.tone}
        onDismiss={() => setToast({ text: "", tone: "info" })}
      />
      {exportFile ? (
        <FloatingToast
          message="家庭数据已准备好；如果浏览器没有自动保存，可点击右侧链接保存文件。离开此页面后下载链接失效。"
          tone="success"
          duration={0}
          onDismiss={() => setExportFile(null)}
        >
          <a href={exportFile.href} download={exportFile.name}>
            保存家庭数据文件
          </a>
        </FloatingToast>
      ) : null}

      <div className="account-section-head">
        <div className="account-section-title-group">
          <h2>{student ? "本地备份导入与数据清理" : "家庭数据导出与隐私"}</h2>
          <InfoPopover label="数据说明" title="备份导入与数据保留说明">
            {student ? (
              <p>
                支持从本地版逐个档案导出 <code>cstf-backup v1</code>{" "}
                文件并导入到 {student.nickname}。本地备份会保留；历史摘要不产生可消费余额、奖励或虚构作答。
              </p>
            ) : (
              <p>
                支持导出全家庭结构化数据 JSON（含家庭设置、所有孩子档案、教材历史、逐次作答与知识点诊断快照）。
              </p>
            )}
            <p>{policy?.notice ?? "正在读取备份保留策略…"}</p>
          </InfoPopover>
        </div>
      </div>

      {student ? (
        <div className="portability-upload-zone">
          <div>
            <strong>导入本地学习备份（cstf-backup v1）</strong>
            <small>
              选择单个孩子的 JSON 备份文件（不超过 5 MB），系统将在弹窗中展示映射与冲突预检报告
            </small>
          </div>
          <label className="account-field" style={{ margin: 0 }}>
            <span>选择这个孩子的备份文件</span>
            <input
              type="file"
              accept="application/json,.json"
              disabled={busy || !!student.archived_at}
              onChange={(e) => {
                void upload(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>
        </div>
      ) : (
        <div className="portability-upload-zone">
          <div>
            <strong>导出全家庭完整学习数据包</strong>
            <small>
              包含家庭所有孩子的档案、教材配置、学习记录与知识点诊断快照
            </small>
          </div>
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setToast({ text: "", tone: "info" });
              try {
                const data = await api("/family/export");
                const fileName = `congcong-family-${new Date().toISOString().slice(0, 10)}.json`;
                const href = URL.createObjectURL(
                  new Blob([JSON.stringify(data, null, 2)], {
                    type: "application/json",
                  }),
                );
                setExportFile({ href, name: fileName });
                const link = document.createElement("a");
                link.href = href;
                link.download = fileName;
                link.click();
              } catch (e) {
                setToast({
                  text: e instanceof Error ? e.message : "导出失败",
                  tone: "error",
                });
              } finally {
                setBusy(false);
              }
            }}
          >
            下载全家庭数据
          </button>
        </div>
      )}

      {student || account.family?.role === "owner" ? (
        <div className="parent-danger-zone">
          <div>
            <strong>
              {student
                ? `永久删除 ${name} 的学习档案与关联账号`
                : "永久注销并删除整个家庭账号"}
            </strong>
            <small>
              {student
                ? "此操作不可恢复，将清除该孩子的全部配置、作答、奖励及独立学生登录账号"
                : "此操作不可恢复，将删除家庭下全部孩子与家长账号"}
            </small>
          </div>
          <button
            type="button"
            className="danger-outline"
            disabled={busy || !policy}
            onClick={() => setDeleting(true)}
          >
            {student ? "删除这个学生及关联登录账号" : "删除整个家庭及家庭账号"}
          </button>
        </div>
      ) : (
        <small>整个家庭的删除仅对家庭所有者开放。</small>
      )}

      <ModalDialog
        open={Boolean(preview && student)}
        title="备份导入预检报告"
        subtitle={student ? `目标档案：${student.nickname}` : undefined}
        onClose={() => setPreview(null)}
      >
        {preview && student ? (
          <div>
            <p>
              可映射 <strong>{preview.report.mapped_lessons}</strong> 节旧课程、
              <strong>{preview.report.mapped_mistakes}</strong> 条错题摘要；
              {preview.report.unmapped.length} 项未映射、
              {preview.report.conflicts.length} 项与云端课程重叠。
            </p>
            <ul>
              {preview.report.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
            <details>
              <summary>查看完整映射与冲突报告</summary>
              <pre
                style={{
                  overflow: "auto",
                  maxHeight: 260,
                  whiteSpace: "pre-wrap",
                  overflowWrap: "anywhere",
                }}
              >
                {JSON.stringify(preview.report, null, 2)}
              </pre>
            </details>
            <div className="account-actions" style={{ marginTop: 16 }}>
              <button
                type="button"
                disabled={busy || preview.confirmed}
                onClick={async () => {
                  setBusy(true);
                  setToast({ text: "", tone: "info" });
                  try {
                    const value = await post<Preview>(
                      `/students/${student.id}/imports/confirm`,
                      {
                        preview_id: preview.preview_id,
                        source_hash: preview.source_hash,
                        revision: preview.revision,
                      },
                    );
                    setPreview(value);
                    setToast({
                      text: `已将本地备份导入到 ${student.nickname}。`,
                      tone: "success",
                    });
                    onImported();
                  } catch (e) {
                    setToast({
                      text: e instanceof Error ? e.message : "确认失败",
                      tone: "error",
                    });
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {preview.confirmed
                  ? "已确认导入"
                  : `确认导入到 ${student.nickname}`}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => setPreview(null)}
              >
                关闭预检
              </button>
            </div>
          </div>
        ) : null}
      </ModalDialog>

      <ModalDialog
        open={deleting}
        title={student ? `确认永久删除 ${name}` : "确认永久删除整个家庭"}
        subtitle="高危操作 · 删除后不可恢复"
        onClose={() => {
          setDeleting(false);
          setConfirmation("");
        }}
        size="sm"
      >
        <div role="alert">
          <p>
            {student
              ? `将永久删除 ${name} 的档案、教材配置、作答、摘要、奖励、未完成会话与学生登录账号，撤销两类学习会话。其他孩子不受影响。`
              : `将永久删除 ${name} 的全部孩子、学习数据、家长和学生账号。部署管理员不受影响。`}
          </p>
          <p>{policy?.notice} 请同时清理自己的下载副本。</p>
          <label className="account-field">
            输入“{name}”确认范围
            <input
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              autoComplete="off"
            />
          </label>
          <div className="account-actions" style={{ marginTop: 16 }}>
            <button
              type="button"
              className="danger"
              disabled={busy || confirmation !== name || !policy}
              onClick={async () => {
                setBusy(true);
                setToast({ text: "", tone: "info" });
                try {
                  const target = student?.id ?? account.family!.id;
                  deleteKey.current ??= crypto.randomUUID();
                  await api(
                    `${student ? `/students/${target}` : "/account"}?confirm=${encodeURIComponent(target)}`,
                    {
                      method: "DELETE",
                      headers: { "Idempotency-Key": deleteKey.current },
                    },
                  );
                  setDeleting(false);
                  announceSessionChange();
                  onDeleted();
                  if (!student) window.location.assign("/login/");
                } catch (e) {
                  setToast({
                    text: e instanceof Error ? e.message : "删除失败，请重新核对",
                    tone: "error",
                  });
                } finally {
                  setBusy(false);
                }
              }}
            >
              确认永久删除
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setDeleting(false);
                setConfirmation("");
              }}
            >
              取消
            </button>
          </div>
        </div>
      </ModalDialog>
    </>
  );

  return embedded ? <div>{body}</div> : <section className="account-card">{body}</section>;
}
