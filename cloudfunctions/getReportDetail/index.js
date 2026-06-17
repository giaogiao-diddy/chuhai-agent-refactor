const { db, getContext } = require("./shared/db");

async function getByAssessmentId(assessmentId, openid) {
  const result = await db.collection("reports")
    .where({ assessment_id: assessmentId, openid })
    .limit(1)
    .get();
  return result.data[0] || null;
}

exports.main = async (event) => {
  const { OPENID } = getContext();
  let report = null;

  if (event.report_id) {
    const result = await db.collection("reports").doc(event.report_id).get();
    report = result.data || null;
  } else if (event.assessment_id) {
    report = await getByAssessmentId(event.assessment_id, OPENID);
  }

  if (!report || report.openid !== OPENID) {
    throw new Error("报告不存在或无权访问");
  }

  if (event.full && !report.is_unlocked) {
    return {
      ok: false,
      error: "完整报告尚未解锁",
      report_id: report._id,
      assessment_id: report.assessment_id,
      is_unlocked: false,
    };
  }

  const visibleReport = event.full
    ? report.report_json
    : {
      hero: report.report_json.hero,
      summary_report: report.report_json.summary_report,
      is_partial: true,
    };

  return {
    ok: true,
    report_id: report._id,
    assessment_id: report.assessment_id,
    is_unlocked: !!report.is_unlocked,
    report: visibleReport,
  };
};
