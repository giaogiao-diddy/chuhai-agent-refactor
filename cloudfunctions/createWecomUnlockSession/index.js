const { db, getContext, now } = require("./shared/db");

const QR_CODE_URL = "/images/wecom-sales.png";

exports.main = async (event) => {
  const { OPENID } = getContext();
  const assessmentId = event.assessment_id;
  const reportResult = await db.collection("reports")
    .where({ assessment_id: assessmentId, openid: OPENID })
    .limit(1)
    .get();

  if (reportResult.data.length === 0) {
    throw new Error("报告不存在或无权访问");
  }

  const report = reportResult.data[0];
  if (report.is_unlocked) {
    return {
      ok: true,
      is_unlocked: true,
      message: "完整报告已解锁",
      qr_code_url: QR_CODE_URL,
      consultant_name: "企微顾问",
      polling_interval: 2,
      enable_mock_unlock: true,
    };
  }

  const existing = await db.collection("wecom_unlock_sessions")
    .where({ assessment_id: assessmentId, openid: OPENID, status: "pending" })
    .limit(1)
    .get();

  if (existing.data.length === 0) {
    await db.collection("wecom_unlock_sessions").add({
      data: {
        openid: OPENID,
        assessment_id: assessmentId,
        report_id: report._id,
        status: "pending",
        created_at: now(),
        updated_at: now(),
      },
    });
  }

  return {
    ok: true,
    is_unlocked: false,
    message: "请扫码添加企业微信顾问，添加成功后系统将解锁完整报告。",
    qr_code_url: QR_CODE_URL,
    consultant_name: "企微顾问",
    polling_interval: 2,
    enable_mock_unlock: true,
  };
};
