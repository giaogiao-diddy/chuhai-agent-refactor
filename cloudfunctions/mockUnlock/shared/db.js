const cloud = require("wx-server-sdk");

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV,
});

const db = cloud.database();
const _ = db.command;

function getContext() {
  return cloud.getWXContext();
}

function now() {
  return db.serverDate();
}

module.exports = {
  cloud,
  db,
  _,
  getContext,
  now,
};
