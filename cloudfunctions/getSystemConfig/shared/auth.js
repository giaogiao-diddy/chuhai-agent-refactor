function parseAdminOpenids(value) {
  if (typeof value !== "string") {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function isAdminOpenid(openid) {
  const adminOpenids = parseAdminOpenids(
    process.env.ADMIN_OPENIDS || process.env.LB_ADMIN_OPENIDS || ""
  );
  return !!openid && adminOpenids.includes(openid);
}

module.exports = {
  isAdminOpenid,
  parseAdminOpenids,
};
