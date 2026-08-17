export const buildLineShareUrl = (text: string) => {
    const normalized = text.trim();
    return `https://line.me/R/msg/text/?${encodeURIComponent(normalized)}`;
};