import type { ZodSchema } from 'zod';

export const zodResolver = (schema: ZodSchema): any => async (values: any) => {
  const result = schema.safeParse(values);
  if (result.success) {
    return { values: result.data, errors: {} };
  }

  const errors: Record<string, any> = {};
  result.error.issues.forEach((issue) => {
    const fieldName = issue.path.join('.');
    errors[fieldName] = {
      message: issue.message,
      type: issue.code
    };
  });

  return { values: {}, errors };
};
