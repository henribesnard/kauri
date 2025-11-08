import questionsMarkdown from '../../../../Tests/questions_demo_entreprises.md?raw';

const questionLinePattern = /^\s*\d+\.\s+(.*)$/;

const parseQuestionsFromMarkdown = (markdown: string): string[] => {
  return markdown
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => questionLinePattern.test(line))
    .map((line) => line.replace(questionLinePattern, '$1').trim())
    .filter((line): line is string => Boolean(line));
};

const getSecureRandomInt = (exclusiveMax: number): number => {
  if (exclusiveMax <= 1) {
    return 0;
  }

  const cryptoApi =
    typeof globalThis !== 'undefined' ? (globalThis.crypto as Crypto | undefined) : undefined;

  if (cryptoApi?.getRandomValues) {
    const buffer = new Uint32Array(1);
    cryptoApi.getRandomValues(buffer);
    return Math.floor((buffer[0] / (0xffffffff + 1)) * exclusiveMax);
  }

  return Math.floor(Math.random() * exclusiveMax);
};

const shuffle = (list: string[]): string[] => {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = getSecureRandomInt(i + 1);
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

export const suggestedQuestionsCatalog = parseQuestionsFromMarkdown(questionsMarkdown);

export const getRandomSuggestedQuestions = (count = 4): string[] => {
  if (count <= 0 || suggestedQuestionsCatalog.length === 0) {
    return [];
  }

  const selectionCount = Math.min(count, suggestedQuestionsCatalog.length);
  return shuffle(suggestedQuestionsCatalog).slice(0, selectionCount);
};
