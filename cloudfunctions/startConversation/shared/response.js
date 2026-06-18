function success(data) {
  return {
    success: true,
    data: data || {},
  };
}

function fail(errorCode, errorMessage) {
  return {
    success: false,
    errorCode,
    errorMessage,
  };
}

function fromError(error, fallbackCode, fallbackMessage) {
  return fail(
    error && error.errorCode ? error.errorCode : fallbackCode,
    error && error.message ? error.message : fallbackMessage
  );
}

module.exports = {
  fail,
  fromError,
  success,
};
