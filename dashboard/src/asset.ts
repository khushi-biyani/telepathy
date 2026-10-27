/** URL of a file in public/, wherever the site is served from (the domain root locally, a sub-folder on GitHub Pages). */
export const asset = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\//, "")}`;
