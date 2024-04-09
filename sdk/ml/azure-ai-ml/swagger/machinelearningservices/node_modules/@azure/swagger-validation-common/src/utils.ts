//move @azure/rest-api-specs-scripts utils here

/**
 * Gets the name of the target branch to which the PR is sent. We are using the environment
 * variable provided by travis-ci. It is called TRAVIS_BRANCH. More info can be found here:
 * https://docs.travis-ci.com/user/environment-variables/#Default-Environment-Variables
 * If the environment variable is undefined then the method returns 'master' as the default value.
 * @returns {string} branchName The target branch name.
 */
export const getTargetBranch = (): string => {
  let result = process.env["TRAVIS_BRANCH"] || "master";
  result = result.trim();
  return result;
};

export const blobHref = (file: string) => {
  return file
    ? `https://github.com/${process.env.TRAVIS_REPO_SLUG}/blob/${process.env.TRAVIS_PULL_REQUEST_SHA}/${file}`
    : "";
};

export const targetHref = (file: string) => {
  return file
    ? `https://github.com/${
        process.env.TRAVIS_REPO_SLUG
      }/blob/${getTargetBranch()}/${file}`
    : "";
};

export const getRelativeSwaggerPathToRepo = (filePath: string): string => {
  const position = filePath.search("specification");
  return filePath.substring(position, filePath.length);
};

/**
 * For breaking change. Trim file path pattern to github style.
 * E.g. Input: specification/redis/resource-manager/Microsoft.Cache/preview/2019-07-01/redis.json:191:5
 *      Output: specification/redis/resource-manager/Microsoft.Cache/preview/2019-07-01/redis.json#L191:5
 * @param filePath
 */
export const getGithubStyleFilePath = (filePath: string): string => {
  const regex = /(.json:)/;
  return filePath.replace(regex, ".json#L");
};
