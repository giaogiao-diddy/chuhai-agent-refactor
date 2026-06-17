function feasibilityTag(score) {
  if (score <= 20) {
    return "观察准备型";
  }
  if (score <= 35) {
    return "轻量试探型";
  }
  if (score <= 50) {
    return "基础具备型";
  }
  return "优先布局型";
}

function leadPriority(score) {
  if (score >= 45) {
    return "P0-立即跟进";
  }
  if (score >= 30) {
    return "P1-重点跟进";
  }
  if (score >= 18) {
    return "P2-培育跟进";
  }
  return "P3-低频触达";
}

function calculateScores(answers) {
  const feasibility_score = answers.reduce((sum, answer) => {
    return sum + ((answer.score_detail && answer.score_detail.feasibility_score) || 0);
  }, 0);
  const lead_score = answers.reduce((sum, answer) => {
    return sum + ((answer.score_detail && answer.score_detail.lead_score) || 0);
  }, 0);

  return {
    feasibility_score,
    lead_score,
    feasibility_tag: feasibilityTag(feasibility_score),
    lead_priority: leadPriority(lead_score),
  };
}

module.exports = {
  calculateScores,
  feasibilityTag,
  leadPriority,
};
