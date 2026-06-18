const COLLECTION_SCHEMAS = {
  assessments: {
    description: "测评记录。所有读写必须绑定 openid，禁止信任前端传入 openid。",
    indexes: [
      { name: "idx_openid_created_at", keys: { openid: 1, createdAt: -1 } },
      { name: "idx_openid_status", keys: { openid: 1, status: 1 } },
    ],
    fields: {
      openid: "String",
      user_id: "String",
      status: '"in_progress" | "completed"',
      branch: '"common" | "has_overseas" | "no_overseas" | null',
      basicInfo: {
        companyName: "String",
        industry: "String",
        industryCategory: "String",
        mainProduct: "String",
        currentSalesRegions: "String[]",
        targetMarkets: "String[]",
        annualRevenue: "String",
        hasForeignTradeExperience: "Boolean",
      },
      feasibility_score: "Number, default 0, 0-100百分制",
      lead_score: "Number, default 0, 0-100百分制",
      unlockedFullReport: "Boolean",
      addedWechat: "Boolean",
    },
  },
  questions: {
    description: "动态配置化题库。运行时题流只能从该集合读取。",
    indexes: [
      { name: "uniq_question_id", keys: { question_id: 1 }, unique: true },
      { name: "idx_active_branch_sort", keys: { is_active: 1, branch: 1, sort_order: 1 } },
    ],
    fields: {
      question_id: "Number, unique",
      title: "String",
      description: "String | empty",
      dimension: '"feasibility" | "lead"',
      branch: '"common" | "has_overseas" | "no_overseas"',
      type: '"radio" | "checkbox" | "text"',
      options: [
        {
          option_id: "Number",
          option_text: "String",
          score: "Number",
        },
      ],
      sort_order: "Number",
      is_active: "Boolean",
    },
  },
  system_config: {
    description: "全局系统配置。固定唯一文档 _id=global_config。",
    indexes: [
      { name: "_id_", keys: { _id: 1 } },
    ],
    fields: {
      _id: '"global_config"',
      wecom_qr_url: "String",
      ai_report_enabled: "Boolean",
      benefit_minutes_default: "Number",
      announcement: "String",
    },
  },
  consultant_notes: {
    description: "顾问跟进状态。一个测评对应一条跟进记录。",
    indexes: [
      { name: "uniq_assessment_id", keys: { assessment_id: 1 }, unique: true },
      { name: "idx_status_updated_at", keys: { status: 1, updated_at: -1 } },
    ],
    fields: {
      assessment_id: "String",
      status: '"uncontacted" | "contacted" | "booked" | "closed"',
      remark: "String",
      updated_at: "Timestamp",
    },
  },
};

const QUESTION_DOCUMENT_EXAMPLE = {
  question_id: 1001,
  title: "您目前是否已经有海外订单或海外客户？",
  description: "这道题用于区分已有外贸基础和完全未出海的企业。",
  dimension: "feasibility",
  branch: "common",
  type: "radio",
  options: [
    { option_id: 1, option_text: "已有稳定海外订单", score: 4, branch_to: "has_overseas" },
    { option_id: 2, option_text: "完全没有海外业务", score: 1, branch_to: "no_overseas" },
  ],
  sort_order: 50,
  is_active: true,
};

module.exports = {
  COLLECTION_SCHEMAS,
  QUESTION_DOCUMENT_EXAMPLE,
};
