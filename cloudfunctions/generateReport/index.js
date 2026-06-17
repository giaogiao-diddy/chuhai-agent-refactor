const completeAssessment = require("../completeAssessment/index");

exports.main = async (event) => {
  return completeAssessment.main(event);
};
