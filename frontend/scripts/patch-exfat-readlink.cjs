const fs = require("fs");

function normalizeReadlinkError(error) {
  if (error && error.code === "EISDIR") {
    error.code = "EINVAL";
  }
  return error;
}

const originalReadlink = fs.readlink;
const originalReadlinkSync = fs.readlinkSync;
const originalPromisesReadlink = fs.promises && fs.promises.readlink;

fs.readlink = function patchedReadlink(path, options, callback) {
  if (typeof options === "function") {
    callback = options;
    options = undefined;
  }
  return originalReadlink.call(fs, path, options, (error, result) => {
    callback(error ? normalizeReadlinkError(error) : null, result);
  });
};

fs.readlinkSync = function patchedReadlinkSync(path, options) {
  try {
    return originalReadlinkSync.call(fs, path, options);
  } catch (error) {
    throw normalizeReadlinkError(error);
  }
};

if (originalPromisesReadlink) {
  fs.promises.readlink = async function patchedPromisesReadlink(path, options) {
    try {
      return await originalPromisesReadlink.call(fs.promises, path, options);
    } catch (error) {
      throw normalizeReadlinkError(error);
    }
  };
}
