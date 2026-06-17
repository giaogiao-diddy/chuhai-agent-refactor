const { db, getContext, now } = require("./shared/db");

exports.main = async () => {
  const { OPENID } = getContext();

  const created = await db.collection("assessments").add({
    data: {
      openid: OPENID,
      status: "in_progress",
      branch: null,
      feasibility_score: 0,
      lead_score: 0,
      feasibility_tag: null,
      lead_priority: null,
      is_unlocked: false,
      created_at: now(),
      updated_at: now(),
      completed_at: null,
    },
  });

  return {
    ok: true,
    assessment_id: created._id,
  };
};
