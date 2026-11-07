"use client";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  Field,
  Message,
} from "@/components/account/AccountShell";
import {
  post,
  announceSessionChange,
  type Account,
} from "@/lib/api/client";
import { useLearningClient } from "@/components/learning/LearningProvider";
import { CloudEconomy } from "@/components/learning/CloudEconomy";
import { useChildLogout } from "./ChildShell";
import { ForestGuide } from "./ForestGuide";
import { LegacySummary } from "@/components/learning/LegacySummary";
import { cloudReports } from "@/lib/learning/reports";
import { downloadJSON } from "@/components/account/PortabilityPanel";
export function CloudCottage({ account }: { account: Account }) {
  const client = useLearningClient();
  const logout = useChildLogout();
  const [parentHelp, setParentHelp] = useState(false);
  const router = useRouter(),
    [profile, setProfile] = useState<{
      nickname: string;
      grade: number;
    } | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    let mounted = true;
    void client.getProfile()
      .then((value) => { if (mounted) setProfile(value); })
      .catch((e) => {
        if (mounted) setError(e.message);
      });
    return () => { mounted = false; };
  }, [client]);
  async function restore(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = event.currentTarget, password = new FormData(form).get("password"); form.reset();
    try { const next = await post<Account>("/mode/parent", {password}); announceSessionChange(); router.replace(next.destination); }
    catch(e) { setError(e instanceof Error ? e.message : "验证失败"); }
    finally { setBusy(false); }
  }
  return <main className="account-card forest-main"><section className="forest-mission"><div className="forest-welcome"><div><h1>{profile ? `${profile.nickname}的小屋` : "我的小屋"}</h1></div><ForestGuide/></div><Message text={error}/><CloudEconomy/>
    <button className="secondary forest-parent-entry" aria-expanded={parentHelp} onClick={()=>setParentHelp(!parentHelp)}>家长与账号 {parentHelp ? "−" : "+"}</button>
    {parentHelp ? <section className="forest-parent-help">
      <p>查看学习记录，或者帮孩子处理遇到的问题。</p>
      <button className="secondary" onClick={() => downloadJSON("congcong-question-reports.json", { schema: "cstf-question-reports", version: 1, student_id: client.scope.studentId, reports: cloudReports(client.scope) })}>导出问题记录</button>
      <LegacySummary studentId={client.scope.studentId}/>
      {account.role === "parent" ? (
        <details>
          <summary>返回家长端</summary>
          <p>共享此登录的标签页也处于孩子模式，返回需要家长密码。</p>
          <form onSubmit={restore}>
            <Field label="家长密码">
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                required
                maxLength={128}
              />
            </Field>
            <button disabled={busy}>验证并返回</button>
          </form>
        </details>
      ) : (
        <p>需要家长帮助时，请退出后由家长账号登录。</p>
      )}<button className="forest-account-exit secondary" onClick={logout}>退出当前账号</button></section> : null}</section></main>;
}
