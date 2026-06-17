const { db, getContext } = require("./shared/db");

exports.main = async () => {
  const { OPENID } = getContext();
  const result = await db.collection("reports")
    .where({ openid: OPENID })
    .orderBy("created_at", "desc")
    .get();

  return {
    ok: true,
    reports: result.data,
  };
};
