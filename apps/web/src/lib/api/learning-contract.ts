/** 与 apps/api/app/learning/schemas.py 对应；权威成绩只从服务端读取。 */
export type LearningKind =
  | "lesson"
  | "challenge"
  | "jump"
  | "story"
  | "number_review"
  | "review"
  | "reading";

export type QuestionRef = {
  uid: string;
  version: string;
  source_question_id?: number;
};

export type PublicQuestion = QuestionRef & {
  id: number;
  type:
    | "true_false"
    | "choice"
    | "fill_blank"
    | "calculation"
    | "word_problem"
    | "fill_blank_text"
    | "word_order"
    | "matching";
  question: string;
  options: string[];
  score: number;
  difficulty: number;
  knowledge_point: string;
  audio: { question: string | null; options: (string | null)[] | null } | null;
  numberTask: {
    hint_count?: number;
    stage: "guided" | "independent" | "transfer";
    visual: Record<string, unknown>;
    hints: string[];
  } | null;
  input_keyboard?: { candidates: string[]; language: "letters" | "text"; max_length: number } | null;
};

export type AnswerFeedback = {
  attempt_id: string;
  correct: boolean;
  first_attempt: boolean;
  answer: string;
  explanation: string;
  explanation_audio: string | null;
  evidence_sentence_indices: number[];
  grading_rule_version: string;
  submitted_answer?: string | null;
  submitted_evidence_indices?: number[];
};

export type LearningSessionView = {
  id: string;
  student_id: string;
  kind: LearningKind;
  book_id: string | null;
  source_id: string | null;
  status: "active" | "completed";
  revision: number;
  cursor: number;
  sources: Record<string, unknown>[];
  checkpoint: {
    pending: number[];
    attempted: number[];
    solved: number[];
    first_correct: number;
    attempt_count: number;
    target_unit: number | null;
    reading_kind: "listen" | "followup" | null;
    hint_levels: Record<string, number>;
    matching_pairs?: Partial<Record<string, string>>;
    draft: {
      answer?: string;
      intro_page?: number;
      visual_draft?: number[];
      evidence_sentence_indices?: number[];
    };
  };
  question: PublicQuestion | null;
  feedback: AnswerFeedback | null;
  settlement?: Record<string, unknown> | null;
};

export type AnswerSubmission = {
  revision: number;
  client_at: string;
  question_uid: string;
  question_version: string;
  answer: string;
  declared_duration_ms?: number;
  hint_level?: number;
  evidence_sentence_indices?: number[];
};
