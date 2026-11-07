import assert from "node:assert/strict";
import fs from "node:fs";
import Module from "node:module";
import path from "node:path";
import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { AppRouterContext } from "next/dist/shared/lib/app-router-context.shared-runtime";
import type {
  KnowledgePointEvidenceDetailResponse,
  KnowledgePointMasteryItem,
  StudentDiagnosticsResponse,
} from "../../apps/web/src/components/account/StudentDiagnosticsPanel";
import type { Account } from "../../apps/web/src/lib/api/client";

(Module as unknown as { _extensions: Record<string, () => void> })._extensions[
  ".css"
] = () => {};

function makeKp(
  overrides: Partial<KnowledgePointMasteryItem> & { id: string; title: string }
): KnowledgePointMasteryItem {
  return {
    id: overrides.id,
    subject_code: overrides.subject_code ?? "math",
    book_id: overrides.book_id ?? "g1up",
    unit_number: overrides.unit_number ?? 1,
    unit_title: overrides.unit_title ?? "第一单元 5以内数的认识和加、减法",
    lesson_id: overrides.lesson_id ?? "g1up-u1-kp1",
    scope_kind: overrides.scope_kind ?? "lesson",
    code: overrides.code ?? "lesson:g1up-u1-kp1",
    title: overrides.title,
    description: overrides.description ?? "核心概念说明",
    sort_order: overrides.sort_order ?? 1,
    status: overrides.status ?? "needs_review",
    status_label: overrides.status_label ?? "需复习",
    diagnostic_rule_version: "diag-v1",
    reason_code: overrides.reason_code ?? "first_wrong_remediated_same_session",
    reason_text:
      overrides.reason_text ??
      "首答出错（0/1），虽已完成当堂回炉订正（1/1），仍需隔次独立练习巩固",
    total_questions_available: overrides.total_questions_available ?? 6,
    distinct_questions_attempted: overrides.distinct_questions_attempted ?? 1,
    distinct_sessions: overrides.distinct_sessions ?? 1,
    distinct_days: overrides.distinct_days ?? 1,
    total_attempts: overrides.total_attempts ?? 2,
    first_attempt_count: overrides.first_attempt_count ?? 1,
    first_correct_count: overrides.first_correct_count ?? 0,
    unassisted_first_correct_count: overrides.unassisted_first_correct_count ?? 0,
    hint_assisted_count: overrides.hint_assisted_count ?? 0,
    retry_attempt_count: overrides.retry_attempt_count ?? 1,
    retry_correct_count: overrides.retry_correct_count ?? 1,
    first_attempt_accuracy: overrides.first_attempt_accuracy ?? 0,
    unassisted_first_accuracy: overrides.unassisted_first_accuracy ?? 0,
    overall_accuracy: overrides.overall_accuracy ?? 0.5,
    last_attempted_at: overrides.last_attempted_at ?? "2026-11-05T08:30:00Z",
    related_has_evidence: overrides.related_has_evidence ?? false,
    related_points: overrides.related_points ?? [],
  };
}

function makeDiagResponse(
  studentId: string,
  subjectCode: string,
  bookId: string,
  bookTitle: string,
  kpTitle: string
): StudentDiagnosticsResponse {
  const kpNeedsReview = makeKp({
    id: `kp-${bookId}-1`,
    subject_code: subjectCode,
    book_id: bookId,
    title: kpTitle,
    status: "needs_review",
    status_label: "需复习",
    related_points: [
      {
        kp_id: `kp-${bookId}-legacy`,
        book_id: "g1up-2026",
        lesson_id: "g1up-2026-u1-kp1",
        code: "lesson:g1up-2026-u1-kp1",
        title: kpTitle,
        relation_kind: "supersedes_exact_title",
        direction: "incoming",
        status: "mastered",
        status_label: "已掌握",
        first_attempt_count: 3,
      },
    ],
  });
  const kpMastered = makeKp({
    id: `kp-${bookId}-2`,
    subject_code: subjectCode,
    book_id: bookId,
    title: `${bookTitle}·已掌握知识点`,
    status: "mastered",
    status_label: "已掌握",
    reason_code: "multi_evidence_mastered",
    reason_text: "无提示首答 3/3 正确，已覆盖 3 题、2 个学习日",
    first_attempt_count: 3,
    first_correct_count: 3,
    unassisted_first_correct_count: 3,
    distinct_questions_attempted: 3,
    distinct_days: 2,
  });

  return {
    student_id: studentId,
    timezone: "Asia/Shanghai",
    diagnostic_rule_version: "diag-v1",
    mapping_version: "kp-map-v1",
    selected_subject_code: subjectCode,
    selected_book_id: bookId,
    selected_book_title: bookTitle,
    available_books: [
      {
        book_id: "g1up",
        title: "数学一年级上册",
        subject_code: "math",
        subject_name: "数学",
        grade: 1,
        semester: "up",
        edition: "人教版",
        is_current_curriculum: true,
        attempt_count: 5,
      },
      {
        book_id: "g1up-2026",
        title: "数学一年级上册（2026精修）",
        subject_code: "math",
        subject_name: "数学",
        grade: 1,
        semester: "up",
        edition: "人教版2026",
        is_current_curriculum: false,
        attempt_count: 3,
      },
      {
        book_id: "chinese-g1up",
        title: "语文一年级上册",
        subject_code: "chinese",
        subject_name: "语文",
        grade: 1,
        semester: "up",
        edition: "统编版",
        is_current_curriculum: true,
        attempt_count: 2,
      },
      {
        book_id: "english-g3up",
        title: "英语三年级上册",
        subject_code: "english",
        subject_name: "英语",
        grade: 3,
        semester: "up",
        edition: "人教PEP",
        is_current_curriculum: true,
        attempt_count: 4,
      },
    ],
    summary: {
      total_knowledge_points: 10,
      assessed_count: 4,
      mastered_count: 1,
      developing_count: 1,
      needs_review_count: 1,
      insufficient_evidence_count: 1,
      unassessed_count: 6,
      total_attempts: 5,
      legacy_imports_count: 1,
      legacy_exclusion_note:
        "知识点掌握度仅基于云端真实作答证据（attempts）计算，不将经验值（XP）、完课打卡或已导入的旧本地档案摘要折算为掌握度。",
    },
    priority_review: [kpNeedsReview],
    units: [
      {
        unit_number: 1,
        unit_title: "第一单元",
        total_count: 2,
        mastered_count: 1,
        developing_count: 0,
        needs_review_count: 1,
        insufficient_evidence_count: 0,
        unassessed_count: 0,
        knowledge_points: [kpNeedsReview, kpMastered],
      },
    ],
  };
}

function textOf(node: TestRenderer.ReactTestInstance | string): string {
  if (typeof node === "string") return node;
  return (node.children ?? []).map(textOf).join("");
}

function assertNoInlineHintsOrMessages(root: TestRenderer.ReactTestInstance) {
  const hints = root.findAll(
    (node) =>
      typeof node.props?.className === "string" &&
      (node.props.className.split(/\s+/).includes("account-hint") ||
        node.props.className.split(/\s+/).includes("account-message") ||
        node.props.className.split(/\s+/).includes("diag-boundary-note"))
  );
  assert.equal(
    hints.length,
    0,
    "Parent UI must never render inline .account-hint, .account-message, or .diag-boundary-note in DOM flow"
  );
}

async function main() {
  const { ParentDashboard } = await import(
    "../../apps/web/src/components/account/ParentDashboard"
  );
  const { StudentOverview } = await import(
    "../../apps/web/src/components/account/StudentOverview"
  );
  const { StudentDiagnosticsPanel } = await import(
    "../../apps/web/src/components/account/StudentDiagnosticsPanel"
  );

  const win = Object.assign(new EventTarget(), {
    setTimeout: globalThis.setTimeout.bind(globalThis),
    clearTimeout: globalThis.clearTimeout.bind(globalThis),
  });
  Object.assign(globalThis, {
    IS_REACT_ACT_ENVIRONMENT: true,
    window: win,
    document: {
      cookie: "csf_csrf=test-token",
      addEventListener: () => {},
      removeEventListener: () => {},
    },
  });

  let chineseResolver!: (res: Response) => void;
  const requestedPaths: string[] = [];

  globalThis.fetch = async (input: RequestInfo | URL) => {
    const url = String(input);
    requestedPaths.push(url);

    if (url.includes("/students?include_archived=")) {
      return new Response(
        JSON.stringify([
          {
            id: "student-a",
            nickname: "聪聪",
            avatar: "panda",
            birth_month: "2019-09",
            province: "北京",
            city: "北京",
            school: "实验小学",
            school_stage: "primary",
            grade: 1,
            school_year: "2026-2027",
            semester: "up",
            daily_goal_minutes: 20,
            parent_notes: null,
            archived_at: null,
            revision: 1,
          },
          {
            id: "student-b",
            nickname: "明明",
            avatar: "rabbit",
            birth_month: "2017-05",
            province: "北京",
            city: "北京",
            school: "实验小学",
            school_stage: "primary",
            grade: 3,
            school_year: "2026-2027",
            semester: "up",
            daily_goal_minutes: 25,
            parent_notes: null,
            archived_at: null,
            revision: 1,
          },
        ]),
        { status: 200 }
      );
    }

    if (url.endsWith("/privacy/policy")) {
      return new Response(
        JSON.stringify({
          retention_days: 30,
          notice: "服务端每日加密备份默认保留 30 天，到期自动轮转清理。",
        }),
        { status: 200 }
      );
    }

    if (url.endsWith("/curriculum")) {
      return new Response(
        JSON.stringify({
          revision: 1,
          subjects: [
            {
              subject_code: "math",
              enabled: true,
              book_id: "g1up",
              current_unit_number: 1,
            },
          ],
          history: [
            {
              id: "hist-1",
              subject_code: "math",
              book_id: "g1up",
              started_at: "2026-09-01T00:00:00Z",
              ended_at: null,
              snapshot: { title: "数学一年级上册" },
            },
          ],
        }),
        { status: 200 }
      );
    }

    if (url.endsWith("/textbooks")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              id: "g1up",
              subject_code: "math",
              title: "数学一年级上册",
              grade: 1,
              school_system: "六三制",
              publisher_label: "人民教育出版社",
              edition_label: "2024版",
              publication_year: 2024,
              isbn: "9787107380000",
              units: [{ number: 1, title: "第一单元" }],
            },
          ],
        }),
        { status: 200 }
      );
    }

    if (url.endsWith("/subjects")) {
      return new Response(
        JSON.stringify([
          { code: "math", name: "数学" },
          { code: "chinese", name: "语文" },
          { code: "english", name: "英语" },
          { code: "science", name: "科学" },
        ]),
        { status: 200 }
      );
    }

    if (url.endsWith("/summary")) {
      const studentId = url.split("/students/")[1].split("/")[0];
      return new Response(
        JSON.stringify({
          student_id: studentId,
          timezone: "Asia/Shanghai",
          declared_time_ms: 600000,
          week: { starts_on: "2026-11-02", declared_time_ms: 300000 },
          state: { xp: 120, completedLessons: { "g1up-u1-kp1": true } },
          daily: {
            "2026-11-05": {
              attempts: 5,
              lesson_completions: 1,
              reading_completions: 0,
              story_completions: 0,
              declared_time_ms: 300000,
            },
          },
        }),
        { status: 200 }
      );
    }

    if (url.endsWith("/legacy") || url.endsWith("/imports")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }

    if (url.includes("/diagnostics/knowledge-points/")) {
      const parts = url
        .split("/students/")[1]
        .split("/diagnostics/knowledge-points/");
      const studentId = parts[0];
      const kpId = decodeURIComponent(parts[1]);
      const detail: KnowledgePointEvidenceDetailResponse = {
        student_id: studentId,
        timezone: "Asia/Shanghai",
        diagnostic_rule_version: "diag-v1",
        mapping_version: "kp-map-v1",
        knowledge_point: makeKp({
          id: kpId,
          title: "1~5的认识与比大小专项知识点",
          related_points: [
            {
              kp_id: "kp-rel-1",
              book_id: "g1up-2026",
              lesson_id: "g1up-2026-u1-kp1",
              code: "lesson:g1up-2026-u1-kp1",
              title: "1~5的认识与比大小专项知识点",
              relation_kind: "supersedes_exact_title",
              direction: "incoming",
              status: "mastered",
              status_label: "已掌握",
            },
          ],
        }),
        recent_attempts: [
          {
            attempt_id: "att-2",
            session_id: "sess-1",
            question_uid: "lesson:g1up:g1up-u1-kp1:1",
            question_version: "v1",
            book_id: "g1up",
            source_id: "g1up-u1-kp1",
            correct: true,
            first_attempt: false,
            hint_level: 0,
            declared_duration_ms: 4000,
            received_at: "2026-11-05T08:31:00Z",
            mapping_source: "lesson_primary",
          },
          {
            attempt_id: "att-1",
            session_id: "sess-1",
            question_uid: "lesson:g1up:g1up-u1-kp1:1",
            question_version: "v1",
            book_id: "g1up",
            source_id: "g1up-u1-kp1",
            correct: false,
            first_attempt: true,
            hint_level: 1,
            declared_duration_ms: 6000,
            received_at: "2026-11-05T08:30:00Z",
            mapping_source: "lesson_primary",
          },
        ],
      };
      return new Response(JSON.stringify(detail), { status: 200 });
    }

    if (url.includes("/diagnostics")) {
      const studentId = url.split("/students/")[1].split("/")[0];
      const parsed = new URL(url, "https://app.test");
      const subj = parsed.searchParams.get("subject");
      const book = parsed.searchParams.get("book_id");
      if (subj === "chinese") {
        return new Promise<Response>((resolve) => {
          chineseResolver = resolve;
        });
      }
      if (subj === "english") {
        return new Response(
          JSON.stringify(
            makeDiagResponse(
              studentId,
              "english",
              "english-g3up",
              "英语三年级上册",
              "Hello与自我介绍核心句型"
            )
          ),
          { status: 200 }
        );
      }
      if (book === "g1up-2026") {
        return new Response(
          JSON.stringify(
            makeDiagResponse(
              studentId,
              "math",
              "g1up-2026",
              "数学一年级上册（2026精修）",
              "2026精修版·5以内数的分与合"
            )
          ),
          { status: 200 }
        );
      }
      return new Response(
        JSON.stringify(
          makeDiagResponse(
            studentId,
            "math",
            "g1up",
            "数学一年级上册",
            `${studentId}·1~5的认识与比大小`
          )
        ),
        { status: 200 }
      );
    }

    throw new Error(`Unexpected fetch URL: ${url}`);
  };

  // 0. 验证新版 ParentDashboard 顶部孩子切换栏 + 四大分类标签页 + 零内联说明 + 浮框/弹窗体系
  const mockAccount: Account = {
    authenticated: true,
    role: "parent",
    mode: "parent",
    destination: "/parent/",
    context_id: "ctx-parent-1",
    user: {
      id: "user-1",
      login_name: "parent_demo",
      nickname: "聪聪妈妈",
      avatar: "panda",
    },
    family: {
      id: "fam-1",
      name: "聪聪之家",
      timezone: "Asia/Shanghai",
      role: "owner",
    },
    student_id: null,
  };
  const router = {
    replace: () => {},
    push: () => {},
    prefetch: async () => {},
    back: () => {},
    forward: () => {},
    refresh: () => {},
  };

  let dashboardView!: TestRenderer.ReactTestRenderer;
  await act(async () => {
    dashboardView = TestRenderer.create(
      <AppRouterContext.Provider value={router as never}>
        <ParentDashboard account={mockAccount} />
      </AppRouterContext.Provider>
    );
  });

  // 默认选中第一个孩子“聪聪”，展示“学习概况”标签页，且页面零内联 .account-hint / .account-message
  assertNoInlineHintsOrMessages(dashboardView.root);
  const overviewJson = JSON.stringify(dashboardView.toJSON());
  assert.match(overviewJson, /聪聪/);
  assert.match(overviewJson, /的工作台/);
  assert.match(overviewJson, /已完成/);
  assert.doesNotMatch(
    overviewJson,
    /重叠学习时段已自动去重/,
    "静态规则说明未点击前不得直接暴露在主界面 DOM 中"
  );

  // 点击“统计说明” InfoPopover 展开气泡浮框，再关闭
  const statInfoBtn = dashboardView.root
    .findAllByType("button")
    .find(
      (b) =>
        b.props.className?.includes("account-info-trigger") &&
        textOf(b).includes("统计说明")
    )!;
  await act(async () => {
    statInfoBtn.props.onClick();
  });
  assert.match(JSON.stringify(dashboardView.toJSON()), /重叠学习时段已自动去重/);
  await act(async () => {
    statInfoBtn.props.onClick();
  });
  assert.doesNotMatch(JSON.stringify(dashboardView.toJSON()), /重叠学习时段已自动去重/);

  // 切换到“知识点诊断”标签页
  const diagTabBtn = dashboardView.root
    .findAllByType("button")
    .find((b) => textOf(b) === "知识点诊断")!;
  await act(async () => {
    diagTabBtn.props.onClick();
  });
  assertNoInlineHintsOrMessages(dashboardView.root);
  assert.match(JSON.stringify(dashboardView.toJSON()), /student-a·1~5的认识与比大小/);

  // 切换到“教材配置”标签页，验证 2x2 学科网格与选书历史弹窗
  const currTabBtn = dashboardView.root
    .findAllByType("button")
    .find((b) => textOf(b) === "教材配置")!;
  await act(async () => {
    currTabBtn.props.onClick();
  });
  assertNoInlineHintsOrMessages(dashboardView.root);
  assert.ok(
    dashboardView.root.findAllByProps({ className: "curriculum-subject-grid" }).length > 0
  );
  const historyBtn = dashboardView.root
    .findAllByType("button")
    .find((b) => textOf(b).includes("选书历史"))!;
  await act(async () => {
    historyBtn.props.onClick();
  });
  assert.match(JSON.stringify(dashboardView.toJSON()), /共记录/);
  const closeModalBtn = dashboardView.root
    .findAllByType("button")
    .find((b) => b.props["aria-label"] === "关闭弹窗")!;
  await act(async () => {
    closeModalBtn.props.onClick();
  });

  // 切换到“档案与数据”标签页，验证归档弹窗确认与永久删除弹窗确认
  const manageTabBtn = dashboardView.root
    .findAllByType("button")
    .find((b) => textOf(b) === "档案与数据")!;
  await act(async () => {
    manageTabBtn.props.onClick();
  });
  assertNoInlineHintsOrMessages(dashboardView.root);
  const archiveTrigger = dashboardView.root
    .findAllByType("button")
    .find((b) => textOf(b) === "归档档案")!;
  await act(async () => {
    archiveTrigger.props.onClick();
  });
  assert.match(JSON.stringify(dashboardView.toJSON()), /确认归档 聪聪/);
  const cancelArchiveBtn = dashboardView.root
    .findAllByType("button")
    .find((b) => textOf(b) === "取消")!;
  await act(async () => {
    cancelArchiveBtn.props.onClick();
  });

  // 打开顶栏“家庭设置”独立弹窗
  const settingsBtn = dashboardView.root
    .findAllByType("button")
    .find((b) => textOf(b) === "家庭设置")!;
  await act(async () => {
    settingsBtn.props.onClick();
  });
  assert.match(JSON.stringify(dashboardView.toJSON()), /家长资料与全家庭数据/);
  await act(async () => {
    dashboardView.unmount();
  });

  // 1. 验证 StudentOverview (includeDiagnostics=true) 与 5 态掌握度汇总、InfoPopover 边界说明
  let view!: TestRenderer.ReactTestRenderer;
  await act(async () => {
    view = TestRenderer.create(
      <StudentOverview studentId="student-a" includeDiagnostics />
    );
  });
  assertNoInlineHintsOrMessages(view.root);
  const textA = JSON.stringify(view.toJSON());
  assert.match(textA, /知识点掌握诊断/);
  assert.match(textA, /student-a·1~5的认识与比大小/);
  assert.match(textA, /已掌握/);
  assert.match(textA, /巩固中/);
  assert.match(textA, /需复习/);
  assert.match(textA, /证据不足/);
  assert.match(textA, /未评估/);
  assert.doesNotMatch(
    textA,
    /旧本地档案摘要/,
    "诊断边界说明未点击前应隐藏在 InfoPopover 中"
  );

  // 点击“诊断说明”按钮，验证气泡浮框展示诊断边界说明
  const diagInfoBtn = view.root
    .findAllByType("button")
    .find(
      (b) =>
        b.props.className?.includes("account-info-trigger") &&
        textOf(b).includes("诊断说明")
    )!;
  await act(async () => {
    diagInfoBtn.props.onClick();
  });
  assert.match(JSON.stringify(view.toJSON()), /旧本地档案摘要/);
  await act(async () => {
    diagInfoBtn.props.onClick();
  });

  // 2. 验证学科快速切换竞态（先切语文未返回，再切英语，随后语文延迟返回不得覆盖英语）
  const chineseBtn = view.root
    .findAllByType("button")
    .find((b) => b.children.join("") === "语文")!;
  const englishBtn = view.root
    .findAllByType("button")
    .find((b) => b.children.join("") === "英语")!;

  await act(async () => {
    chineseBtn.props.onClick();
  });
  await act(async () => {
    englishBtn.props.onClick();
  });
  assert.match(JSON.stringify(view.toJSON()), /Hello与自我介绍核心句型/);

  await act(async () => {
    chineseResolver(
      new Response(
        JSON.stringify(
          makeDiagResponse(
            "student-a",
            "chinese",
            "chinese-g1up",
            "语文一年级上册",
            "天地人识字诊断（过期响应）"
          )
        ),
        { status: 200 }
      )
    );
  });
  const afterLateChinese = JSON.stringify(view.toJSON());
  assert.match(afterLateChinese, /Hello与自我介绍核心句型/);
  assert.doesNotMatch(
    afterLateChinese,
    /天地人识字诊断（过期响应）/,
    "过期学科响应不得覆盖当前选中的学科"
  );

  // 3. 切回数学并切换历史精修教材版本
  const mathBtn = view.root
    .findAllByType("button")
    .find((b) => b.children.join("") === "数学")!;
  await act(async () => {
    mathBtn.props.onClick();
  });
  const bookSelect = view.root
    .findAllByType("select")
    .find((s) => s.props["aria-label"] === "诊断教材")!;
  await act(async () => {
    bookSelect.props.onChange({ target: { value: "g1up-2026" } });
  });
  assert.match(JSON.stringify(view.toJSON()), /2026精修版·5以内数的分与合/);

  // 4. 点击“查看证据”在 ModalDialog 弹窗中展示单点证据明细，检查首答/同场回炉/提示等级与跨版关联展示
  const evidenceBtn = view.root
    .findAllByType("button")
    .find((b) => b.children.join("") === "查看证据")!;
  await act(async () => {
    evidenceBtn.props.onClick();
  });
  const detailText = JSON.stringify(view.toJSON());
  assert.match(detailText, /知识点证据明细/);
  assert.match(detailText, /同场回炉重做/);
  assert.match(detailText, /使用提示\(L1\)/);
  assert.match(detailText, /跨版同名知识点/);
  assert.ok(
    view.root.findAllByProps({ role: "dialog" }).length >= 1,
    "Evidence detail must be rendered inside a modal dialog"
  );

  // 5. 切换学生身份时自动清空旧明细弹窗并加载新学生诊断
  await act(async () => {
    view.update(<StudentDiagnosticsPanel studentId="student-b" />);
  });
  const textB = JSON.stringify(view.toJSON());
  assert.match(textB, /student-b·1~5的认识与比大小/);
  assert.doesNotMatch(textB, /知识点证据明细/);
  await act(async () => {
    view.unmount();
  });

  // 6. 检查 account.css 与 forest.css 响应式、浮框、选择子优先级与防横向溢出样式契约
  const cssPath = path.resolve(
    process.cwd(),
    "apps/web/src/components/account/account.css"
  );
  const forestCssPath = path.resolve(
    process.cwd(),
    "apps/web/src/components/learning/forest.css"
  );
  const shellPath = path.resolve(
    process.cwd(),
    "apps/web/src/components/account/AccountShell.tsx"
  );
  const css = fs.readFileSync(cssPath, "utf-8");
  const forestCss = fs.readFileSync(forestCssPath, "utf-8");
  const shellCode = fs.readFileSync(shellPath, "utf-8");
  assert.ok(
    shellCode.indexOf('import "../learning/forest.css"') <
      shellCode.indexOf('import "./account.css"'),
    "account.css must be imported after forest.css so parent console button variants are never overridden"
  );
  assert.doesNotMatch(
    forestCss,
    /button:not\(\.forest-question \*\)/,
    "forest.css base button rule must use :where(.forest-question *) to avoid 0,2,1 specificity override"
  );
  assert.match(css, /\.diag-summary-grid/);
  assert.match(css, /\.account-floating-toast/);
  assert.match(css, /\.account-popover-card/);
  assert.match(css, /\.account-modal-card/);
  assert.match(css, /\.account-segmented-tabs/);
  assert.match(css, /\.diag-kp-row[\s\S]*?overflow-wrap:\s*anywhere/);
  assert.match(css, /@media\s*\(max-width:\s*700px\)[\s\S]*?\.diag-summary-grid/);

  console.log(
    "PASS parent-dashboard & knowledge-diagnostics: 4-tab categorized workspace, zero inline hints/messages, InfoPopover, ModalDialog evidence/settings/archive, race protection, and responsive CSS contract."
  );
}

void main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
