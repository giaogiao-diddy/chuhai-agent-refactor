const { db } = require("./shared/db");
const { getQuestionsForBranch } = require("./shared/questionFlow");
const { fromError, success } = require("./shared/response");

exports.main = async (event) => {
  const branch = event && event.branch ? event.branch : null;

  try {
    const config = await getQuestionsForBranch(db, branch);
    return success({
      branch,
      questions: config.questions,
      by_branch: config.by_branch,
      tags: {
        feasibility: [
          { range: [80, 100], label: "高潜力出海企业" },
          { range: [60, 79], label: "具备出海基础，建议启动短视频出海" },
          { range: [40, 59], label: "有出海机会，但需补齐关键能力" },
          { range: [20, 39], label: "建议先做低成本市场验证" },
          { range: [0, 19], label: "当前出海准备度较弱" },
        ],
        lead: [
          { range: [80, 100], label: "A类客户：强意向，优先跟进" },
          { range: [60, 79], label: "B类客户：需求明确，可重点培育" },
          { range: [40, 59], label: "C类客户：有兴趣，需要教育转化" },
          { range: [0, 39], label: "D类客户：低意向，长期养熟" },
        ],
      },
    });
  } catch (err) {
    console.error("getAssessmentConfig 失败:", err);
    return fromError(err, "DB_ERROR", "获取测评配置失败");
  }
};
