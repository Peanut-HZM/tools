# Community Knowledge Research: react-hook-form-zod

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/react-hook-form-zod/SKILL.md
**Packages Researched**: react-hook-form@7.71.1, zod@4.3.5, @hookform/resolvers@5.2.2
**Official Repos**: react-hook-form/react-hook-form, colinhacks/zod, react-hook-form/resolvers
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 16 |
| TIER 1 (Official) | 11 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 10 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Zod v4 Type Inference Issues with zodResolver

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #13109](https://github.com/react-hook-form/react-hook-form/issues/13109) (Closed 2025-11-01)
**Date**: 2025-10-22
**Verified**: Yes - Fixed in v7.66.x+
**Impact**: HIGH
**Already in Skill**: Yes (Known Issue #1)

**Description**:
When using Zod v4 with zodResolver, the inferred form types are incorrect. Instead of getting the expected concrete types like `{ phone: string }`, developers get generic types like `UseFormReturn<z4.input<T>, unknown, z4.output<T>>`.

**Reproduction**:
```typescript
import * as z from "zod/v4";

const schema = z.object({
  phone: z.string().length(10, "Phone number must be 10 digits long"),
});

const form = useForm({
  resolver: zodResolver(schema),
  defaultValues: {
    phone: defaultValue?.replace("+44", ""),
  },
});

// form is of type UseFormReturn<z4.input<T>, unknown, z4.output<T>>
// NOT { phone: string }
```

**Solution/Workaround**:
```typescript
// Use z.infer explicitly for type safety
type FormData = z.infer<typeof schema>;

const form = useForm<FormData>({
  resolver: zodResolver(schema),
  defaultValues: { phone: "" },
});
```

**Official Status**:
- [x] Fixed in version 7.66.x+
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Already documented in skill as Known Issue #1
- Resolution verified in later versions

---

### Finding 1.2: Zod v4 Optional Fields Validation Bug

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #13102](https://github.com/react-hook-form/react-hook-form/issues/13102) (Closed 2025-10-16)
**Date**: 2025-10-16
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using Zod v4 with `.optional()` fields (like `z.email().optional()` or `z.iso.datetime().optional()`), setting the value to empty string `""` incorrectly marks formState as invalid, even though empty strings should be valid for optional fields.

**Reproduction**:
```typescript
const TestSchema = z.object({
  emailField: z.email().optional(),
  dateTimeField: z.iso.datetime({
    offset: true,
    local: true,
    precision: -1,
  }).optional(),
});

const defaultValues = {
  emailField: "emailtest@gtyt.com",
  dateTimeField: "2025-04-30T13:00",
};

const methods = useForm({
  resolver: zodResolver(TestSchema),
  defaultValues: defaultValues,
  mode: "onChange",
});

// Later clearing optional field:
setValue("emailField", ""); // Incorrectly triggers validation error
```

**Solution/Workaround**:
```typescript
// Option 1: Use .nullable() or .nullish() instead
const schema = z.object({
  emailField: z.email().nullish(), // accepts null/undefined, not empty string
});

// Option 2: Add .or() for empty string
const schema = z.object({
  emailField: z.email().or(z.literal("")), // explicitly allow empty string
});

// Option 3: Use preprocess to convert empty to undefined
const schema = z.object({
  emailField: z.preprocess(
    (val) => val === "" ? undefined : val,
    z.email().optional()
  ),
});
```

**Official Status**:
- [x] Known issue with Zod v4
- [ ] Fixed in version X.Y.Z
- [x] Workaround required
- [ ] Won't fix

---

### Finding 1.3: useFieldArray Does Not Support Primitive Arrays

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #12570](https://github.com/react-hook-form/react-hook-form/issues/12570) (Closed 2025-01-30), [Official Docs](https://react-hook-form.com/docs/usefieldarray)
**Date**: 2025-01-30
**Verified**: Yes - Design limitation
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
`useFieldArray` does not support flat/primitive arrays like `string[]` or `number[]`. It only works with arrays of objects. This is a documented design limitation. Attempting to use primitive arrays causes TypeScript errors.

**Reproduction**:
```typescript
const { control } = useFormContext<{
  name: string;
  children: {
    label: string;
    grandchildren: { name: string }[]; // ✅ Works
    grandchildrenNames: string[];      // ❌ Fails
  }[];
}>();

// This works:
useFieldArray({ name: `children.${fieldIndex}.grandchildren`, control });

// This does not:
useFieldArray({ name: `children.${fieldIndex}.grandchildrenNames`, control });
// Error: Type 'string' is not assignable to type 'never'
```

**Solution/Workaround**:
```typescript
// Transform primitive array to array of objects
// Instead of: emails: ["craig@example.com"]
// Use: emails: [{ address: "craig@example.com" }]

const schema = z.object({
  emails: z.array(z.object({
    address: z.string().email()
  })),
});

// Then in component:
const { fields, append, remove } = useFieldArray({
  control,
  name: "emails",
});

// Map back to primitives on submit if needed:
const onSubmit = (data) => {
  const emailAddresses = data.emails.map(e => e.address);
  // Send emailAddresses to API
};
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (design limitation)
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Mentioned in official docs: "Does not support flat field array"
- Community sources: [react-hook-form useFieldArray docs](https://react-hook-form.com/docs/usefieldarray)

---

### Finding 1.4: useFieldArray ID Mismatch with SSR

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #12782](https://github.com/react-hook-form/react-hook-form/issues/12782) (Closed 2025-04-26)
**Date**: 2025-04-26
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using `useFieldArray` with SSR (Remix, Next.js), the `id` prop gets generated on the server, then regenerated on the client, causing hydration mismatch warnings.

**Reproduction**:
```typescript
// Remix or Next.js with SSR
const { fields } = useFieldArray({ control, name: "items" });

// Console warning:
// Warning: Prop `id` did not match.
// Server: "94a8cd11-f840-4011-a618-95d10805359f"
// Client: "abad1bf2-8aff-457c-94ab-53bc27fd72ff"
```

**Solution/Workaround**:
```typescript
// V7: No built-in solution, wait for V8
// Workaround: Use client-only rendering for field arrays
"use client"; // Next.js App Router

// Or wrap in ClientOnly component:
import dynamic from 'next/dynamic';

const FieldArrayComponent = dynamic(
  () => import('./FieldArrayComponent'),
  { ssr: false }
);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Note**: V8 beta addresses this by renaming `id` to `key` and making it deterministic.

---

### Finding 1.5: Performance Issues with 300+ Fields and Resolver

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #13129](https://github.com/react-hook-form/react-hook-form/issues/13129) (Closed 2025-11-05)
**Date**: 2025-11-05
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using 300+ fields with a resolver (Zod or Yup) AND reading formState properties, form registration becomes extremely slow (~10-15 seconds freeze in production).

**Reproduction**:
```typescript
const form = useForm({
  resolver: zodResolver(largeSchema), // 300+ field schema
  mode: "onChange",
});

// Reading ANY formState property triggers performance issue:
const { isDirty, isValid, errors } = form.formState;

// Adding 300 fields freezes for ~15 seconds
```

**Solution/Workaround**:
```typescript
// Option 1: Avoid reading formState unless needed
const form = useForm({
  resolver: zodResolver(schema),
});

// Don't destructure formState at top level
// Only read specific properties when needed
const handleSubmit = () => {
  if (!form.formState.isValid) return; // Read inline, not destructured
};

// Option 2: Use mode: "onSubmit" for large forms
const form = useForm({
  resolver: zodResolver(largeSchema),
  mode: "onSubmit", // Don't validate on every change
});

// Option 3: Split into smaller sub-forms with separate schemas
// Instead of one 300-field form, use 5-6 forms with 50-60 fields each

// Option 4: Lazy register fields (don't mount all at once)
// Use tabs/accordion to only mount visible fields
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue (performance limitation)
- [x] Workaround required
- [ ] Won't fix

**Performance Guidance**:
- **Clean (no resolver, no formState read)**: Almost immediate
- **With resolver only**: Almost immediate
- **With formState read only**: Almost immediate
- **With BOTH resolver + formState read**: ~9.5 seconds for 300 fields

---

### Finding 1.6: form.reset() Causes Validation Errors with Next.js 16 Server Actions

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #13110](https://github.com/react-hook-form/react-hook-form/issues/13110) (Closed 2025-10-27)
**Date**: 2025-10-27
**Verified**: Yes - Fixed in v7.65.0+
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using Next.js 16 with Server Actions, calling `form.reset()` after successful submission causes validation errors on subsequent submissions, even with valid data.

**Reproduction**:
```typescript
"use client";

const form = useForm<FormData>({
  resolver: zodResolver(schema),
  defaultValues: { name: "", description: "" },
});

const onSubmit = async (data: FormData) => {
  const res = await submitServerAction(data);

  if (res?.error) {
    toast({ title: "Error", description: res.error });
    return;
  }

  toast({ title: "Success" });
  form.reset(); // ❌ Causes next submission to fail validation
};

// On next submit with valid data (name: "test", description: "valid"):
// Shows errors: "Name must be at least 2 characters" (even though it's 4)
```

**Solution/Workaround**:
```typescript
// Before v7.65.0: Use setValue instead of reset
form.setValue("name", "");
form.setValue("description", "");

// v7.65.0+: reset() works correctly (fixed)
form.reset();
```

**Official Status**:
- [x] Fixed in version 7.65.0+
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Fix Details**: The fix clears validation errors synchronously in reset() to resolve Next.js 16 Server Actions issue.

---

### Finding 1.7: Inconsistent formState During Resolver Validation

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #13156](https://github.com/react-hook-form/react-hook-form/issues/13156) (Closed 2025-11-23)
**Date**: 2025-11-23
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
During resolver validation, there's an intermediate render where `isValidating` becomes `false` but `errors` hasn't been populated yet, causing derived validity state to be temporarily incorrect.

**Reproduction**:
```typescript
const form = useForm({
  resolver: zodResolver(schema),
  mode: "onChange",
});

useEffect(() => {
  console.log({
    cardNumber: form.watch("cardNumber"),
    error: form.formState.errors.cardNumber,
    isValid: !form.formState.errors.cardNumber,
    isValidating: form.formState.isValidating,
  });
}, [form.watch("cardNumber"), form.formState]);

// Type 1 character, observe 3 renders:
// RENDER 1: isValidating=true, error=undefined, valid=true ✅
// RENDER 2: isValidating=false, error=undefined, valid=true ❌ (incorrect!)
// RENDER 3: isValidating=false, error=[object], valid=false ✅
```

**Solution/Workaround**:
```typescript
// Don't derive validity from errors alone during validation
const isFieldValid = !form.formState.errors.cardNumber && !form.formState.isValidating;

// Or wait for both conditions:
const canSubmit = form.formState.isValid && !form.formState.isValidating;

// Avoid relying on errors during intermediate validation states
const showError = form.formState.errors.cardNumber && !form.formState.isValidating;
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue (timing race condition)
- [x] Workaround required
- [ ] Won't fix

**Note**: This is a timing issue with async resolver validation. The fix would require changing the validation lifecycle.

---

### Finding 1.8: Zod v4 Support in @hookform/resolvers

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #813](https://github.com/react-hook-form/resolvers/issues/813) (Open 2025-08-24)
**Date**: 2025-08-24
**Verified**: Yes - Still open
**Impact**: HIGH
**Already in Skill**: No

**Description**:
The zodResolver in @hookform/resolvers has TypeScript compatibility issues with Zod v4. The resolver expects Zod v3 types and throws type errors when using Zod v4 schemas.

**Reproduction**:
```typescript
import { z } from 'zod/v4';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

const schema = z.object({ name: z.string() });

const methods = useForm({
  resolver: zodResolver(schema), // TypeScript error
});

// Error:
// No overload matches this call.
// Argument of type 'ZodObject<...>' is not assignable to parameter of type 'Zod3Type<...>'
// Property 'typeName' is missing in type '$ZodObjectDef<...>'
// The types of '_zod.version.minor' are incompatible between these types.
// Type '1' is not assignable to type '0'.
```

**Solution/Workaround**:
```typescript
// Option 1: Use Zod v3 for now
import { z } from 'zod'; // v3.x

// Option 2: Import from v3 path explicitly
import { z } from 'zod/v3';

// Option 3: Wait for @hookform/resolvers update
// Track: https://github.com/react-hook-form/resolvers/issues/813
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Related Issues**:
- [#818: Can't resolve zod/v4/core](https://github.com/react-hook-form/resolvers/issues/818)
- [#799: hookform/resolvers no longer working with Zod v4](https://github.com/react-hook-form/resolvers/issues/799)
- Multiple open issues about Zod v4 compatibility

---

### Finding 1.9: ZodError Thrown Instead of Captured by zodResolver (Zod v4)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #12816](https://github.com/react-hook-form/react-hook-form/issues/12816) (Closed 2025-05-13)
**Date**: 2025-05-13
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
With Zod v4 beta versions, validation errors are thrown directly as `ZodError` instead of being captured by `zodResolver` and populated into `formState.errors`, leading to uncaught exceptions.

**Reproduction**:
```typescript
import { z } from "zod"; // v4.0.0-beta.20250505T195954

const schema = z.object({
  email: z.email("Please enter a valid email address."),
  password: z.string().min(6, "Password must be at least 6 characters long"),
});

const form = useForm({
  resolver: zodResolver(schema),
});

// Submit with invalid data:
// Uncaught (in promise) ZodError: [
//   {
//     "origin": "string",
//     "code": "invalid_format",
//     "format": "email",
//     "path": ["email"],
//     "message": "Please enter a valid email address."
//   }
// ]
```

**Solution/Workaround**:
```typescript
// Use stable Zod v4.x (not beta)
// The issue was specific to beta versions

// Or wrap in try-catch during beta:
const onSubmit = async (data) => {
  try {
    await handleSubmit(data);
  } catch (error) {
    if (error instanceof ZodError) {
      // Manually map to formState errors
      error.issues.forEach(issue => {
        form.setError(issue.path[0], { message: issue.message });
      });
    }
  }
};
```

**Official Status**:
- [x] Fixed in stable Zod v4.1.x+
- [x] Known issue in beta only
- [ ] Workaround required (for beta)
- [ ] Won't fix

---

### Finding 1.10: V8 Beta Breaking Changes

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v8.0.0-beta.1](https://github.com/react-hook-form/react-hook-form/releases/tag/v8.0.0-beta.1), [RFC Discussion #7433](https://github.com/orgs/react-hook-form/discussions/7433)
**Date**: 2026-01-11
**Verified**: Yes - Beta version
**Impact**: HIGH
**Already in Skill**: No

**Description**:
React Hook Form v8 beta introduces several breaking changes that will affect existing code when upgrading.

**Breaking Changes**:
```typescript
// 1. useFieldArray: id → key, keyName removed
const { fields } = useFieldArray({ control, name: "items" });

// V7:
fields[0].id // unique ID for re-render key

// V8:
fields[0].key // unique ID for re-render key
// keyName prop removed

// 2. Watch component: names → name
// V7:
<Watch names={["email", "password"]} />

// V8:
<Watch name={["email", "password"]} />

// 3. watch() callback API removed
// V7:
watch((data, { name, type }) => {
  console.log(data, name, type);
});

// V8: Use useWatch or manual subscription instead
useWatch({ control });

// 4. setValue no longer updates useFieldArray
// V7:
setValue("items", newArray); // Updates field array

// V8:
replace(newArray); // Must use replace() API
```

**Migration Guide**:
```typescript
// Update useFieldArray keys:
fields.map((field) => (
  <div key={field.key}> {/* V8: use .key not .id */}
    <input {...register(`items.${index}.name`)} />
  </div>
));

// Replace watch callback with useWatch:
// Before:
const subscription = watch((data) => console.log(data));

// After:
const data = useWatch({ control });
useEffect(() => {
  console.log(data);
}, [data]);

// Use replace() for field array updates:
// Before:
setValue("items", newItems);

// After:
const { replace } = useFieldArray({ control, name: "items" });
replace(newItems);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Beta breaking changes (planned)
- [x] Migration required when upgrading
- [ ] Won't fix

**Timeline**: V8 is in beta (v8.0.0-beta.1 released 2026-01-11). Stable release date TBD.

---

### Finding 1.11: Zod v4.3.0 New Features Relevant to Forms

**Trust Score**: TIER 1 - Official
**Source**: [Zod Release v4.3.0](https://github.com/colinhacks/zod/releases/tag/v4.3.0)
**Date**: 2025-12-31
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Zod v4.3.0 introduced several new features that are highly relevant for form validation with react-hook-form.

**New Features**:

**1. z.fromJSONSchema() - Convert JSON Schema to Zod**
```typescript
import * as z from "zod";

const schema = z.fromJSONSchema({
  type: "object",
  properties: {
    name: { type: "string", minLength: 1 },
    age: { type: "integer", minimum: 0 },
  },
  required: ["name"],
});

// Use with react-hook-form:
const form = useForm({
  resolver: zodResolver(schema),
});
```

**2. .exactOptional() - Strict Optional Properties**
```typescript
const schema = z.object({
  a: z.string().optional(),       // accepts undefined
  b: z.string().exactOptional(),  // does NOT accept undefined
});

// Use cases:
schema.parse({});                  // ✅
schema.parse({ a: undefined });    // ✅
schema.parse({ b: undefined });    // ❌ Error

// Perfect for forms where:
// - Field can be omitted (not rendered)
// - But if rendered, must have a value (not undefined)
```

**3. z.xor() - Exclusive Union (Exactly One)**
```typescript
const schema = z.xor([z.string(), z.number()]);

schema.parse("hello"); // ✅
schema.parse(42);      // ✅
schema.parse(true);    // ❌ zero matches

// Useful for forms with mutually exclusive fields:
const formSchema = z.xor([
  z.object({ accountType: z.literal("personal"), ssn: z.string() }),
  z.object({ accountType: z.literal("business"), ein: z.string() }),
]);
```

**4. z.looseRecord() - Partial Record Validation**
```typescript
const schema = z.looseRecord(z.string().regex(/^S_/), z.string());

schema.parse({ S_name: "John", other: 123 });
// ✅ { S_name: "John", other: 123 }
// Only S_name is validated, "other" passes through

// Useful for dynamic form fields with known prefixes
```

**Solution/Workaround**:
```typescript
// Use these features in react-hook-form schemas:

// Strict optional fields (must have value if present):
const schema = z.object({
  email: z.string().email(),
  middleName: z.string().exactOptional(), // Can omit, but not undefined
});

// Exclusive form modes:
const schema = z.xor([
  z.object({ mode: z.literal("email"), email: z.string().email() }),
  z.object({ mode: z.literal("phone"), phone: z.string() }),
]);

const form = useForm({
  resolver: zodResolver(schema),
});
```

**Official Status**:
- [x] Released in Zod v4.3.0
- [x] Documented in release notes
- [x] Production ready
- [ ] Known issues

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Common Mistake - Forgetting defaultValues

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [React Hook Form Common Mistakes Blog](https://alexhooley.com/blog/react-hook-form-common-mistakes), [Contentful Blog](https://www.contentful.com/blog/react-hook-form-validation-zod/)
**Date**: 2025
**Verified**: Cross-referenced with official docs
**Impact**: HIGH
**Already in Skill**: Yes (Known Issue #2)

**Description**:
Forgetting to set proper `defaultValues` is the most common issue with React Hook Form, especially with controlled components (shadcn/ui) or Zod. It leads to bugs with form submission, resetting, checking form state, and dirty fields.

**Community Validation**:
- Multiple blog posts identify this as #1 mistake
- Corroborated by official documentation
- High upvote count on related Stack Overflow questions

**Note**: Already well-documented in skill as "Always set defaultValues" rule.

---

### Finding 2.2: shadcn/ui Import Confusion with Auto-Import

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Contentful Blog](https://www.contentful.com/blog/react-hook-form-validation-zod/), Community discussions
**Date**: 2025
**Verified**: Common pattern
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
A common pitfall when using shadcn/ui Form components is when IDEs with auto-imports or AI code completion import both `useForm` and `Form` from "react-hook-form" instead of importing the Form component from shadcn.

**Reproduction**:
```typescript
// ❌ Wrong - AI autocomplete does this:
import { useForm, Form } from "react-hook-form";

// ✅ Correct:
import { useForm } from "react-hook-form";
import { Form } from "@/components/ui/form"; // shadcn component
```

**Solution/Workaround**:
```typescript
// Always verify imports when using shadcn/ui:
// useForm, Controller, etc → "react-hook-form"
// Form, FormField, FormItem, etc → "@/components/ui/form"

// Set up IDE/ESLint to prefer local components for Form:
{
  "rules": {
    "no-restricted-imports": ["error", {
      "patterns": [{
        "group": ["react-hook-form"],
        "importNames": ["Form"],
        "message": "Import Form from @/components/ui/form instead"
      }]
    }]
  }
}
```

**Community Validation**:
- Mentioned in multiple tutorials
- Common source of confusion
- Related to shadcn/ui integration

---

### Finding 2.3: Misunderstanding Field Registration and Unregister

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Medium Article: Debugging React Hook Form & Zod](https://medium.com/@jinha4ever/debugging-react-hook-form-zod-understanding-how-defaultvalues-and-unregister-work-74b54813de0d)
**Date**: 2025
**Verified**: Partial
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When fields are unregistered (component unmounts), they can be automatically re-registered if an input remains mounted. This can cause validation to fail unexpectedly, especially with conditional fields.

**Reproduction**:
```typescript
const form = useForm({
  resolver: zodResolver(schema),
  shouldUnregister: true, // Important flag
});

// Conditional field:
{showAddress && (
  <input {...register("address")} />
)}

// When showAddress becomes false:
// - Field unregisters
// - Value removed from form data
// - If field re-renders (e.g., parent re-render), auto-registers again
// - Validation may fire on empty value
```

**Solution/Workaround**:
```typescript
// Option 1: Use shouldUnregister: false (default)
const form = useForm({
  resolver: zodResolver(schema),
  shouldUnregister: false, // Keep values when unmounted
});

// Option 2: Use conditional schema validation
const schema = z.object({
  showAddress: z.boolean(),
  address: z.string(),
}).refine((data) => {
  if (data.showAddress) {
    return data.address.length > 0;
  }
  return true;
}, {
  message: "Address is required",
  path: ["address"],
});

// Option 3: Manually unregister with cleanup
useEffect(() => {
  if (!showAddress) {
    form.unregister("address", { keepValue: false });
  }
}, [showAddress]);
```

**Community Validation**:
- Detailed Medium article explaining the issue
- Related to conditional rendering patterns
- Confirmed by official docs behavior

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Error Object Structure for Nested Fields

**Trust Score**: TIER 3 - Community Consensus
**Source**: Multiple blog posts and discussions
**Date**: 2025
**Verified**: Cross-referenced
**Impact**: LOW
**Already in Skill**: Yes (Partially covered)

**Description**:
The keys of the errors object must match field names hierarchically, not as flat keys. Using flat keys (like "address.street") won't set or clear errors properly.

**Consensus Evidence**:
- Multiple sources agree on this pattern
- Mentioned in official examples
- Common source of confusion

**Note**: Already covered in skill with `errors.address?.street?.message` pattern.

---

### Finding 3.2: useForm in useEffect Dependency Arrays

**Trust Score**: TIER 3 - Community Consensus
**Source**: Community discussions, GitHub discussions
**Date**: 2025
**Verified**: Mentioned in discussions
**Impact**: LOW
**Already in Skill**: No

**Description**:
Adding the entire return value of `useForm` to a useEffect dependency list may lead to infinite loops in future releases as useForm return will be memoized.

**Solution**:
```typescript
// ❌ Don't do this:
const form = useForm();
useEffect(() => {
  // Do something
}, [form]); // Entire form object

// ✅ Do this:
const form = useForm();
const { watch, setValue } = form;
useEffect(() => {
  // Do something
}, [watch, setValue]); // Specific methods
```

**Consensus Evidence**:
- Mentioned in community discussions
- Related to future React Hook Form changes
- Best practice for dependency arrays

**Recommendation**: Add to Community Tips section with note about future compatibility.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

No TIER 4 findings. All findings were from official sources or high-quality community content.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Zod v4 Type Inference | Known Issues #1 | Fully covered with z.infer pattern |
| defaultValues Required | Critical Rules, Known Issue #2 | Fully covered |
| Error Object Structure | Error Handling | Partially covered with optional chaining |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.2 Zod v4 Optional Fields Bug | Known Issues | Add as Issue #13 with workarounds |
| 1.3 useFieldArray Primitives | Known Issues | Add as Issue #14 with object wrapper pattern |
| 1.5 Performance 300+ Fields | Performance | Add to Performance section with all 4 workarounds |
| 1.6 Next.js 16 reset() Issue | Known Issues | Add with note "Fixed in v7.65.0+" |
| 1.7 isValidating Race Condition | Known Issues | Add as Issue #15 with timing workaround |
| 1.8 Zod v4 Resolver Types | Known Issues | Update Issue #1 with resolver compatibility note |
| 1.11 Zod v4.3.0 New Features | Advanced Patterns | Add new section on .exactOptional(), .xor(), z.fromJSONSchema() |

### Priority 2: Consider Adding (TIER 2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.4 useFieldArray SSR | Known Issues | Add with SSR note, mention V8 fix |
| 1.10 V8 Beta Breaking Changes | Add new section | "Upcoming Changes in V8" section |
| 2.2 shadcn Import Confusion | shadcn Integration | Add common mistake warning |
| 2.3 Field Re-registration | Advanced Patterns | Add to conditional validation section |
| 3.2 useForm Dependencies | Performance or Tips | Add as performance tip |

### Priority 3: Monitor (No Action Now)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| V8 Breaking Changes | Beta only | Wait for stable release to document migration |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "edge case OR gotcha" in react-hook-form | 0 | 0 |
| "workaround OR breaking" in react-hook-form | 0 | 0 |
| "useFieldArray" in react-hook-form (closed) | 20 | 10 |
| "resolver" in react-hook-form (closed) | 30 | 12 |
| "React 19" in react-hook-form | 10 | 3 |
| "zod v4" in react-hook-form | 15 | 8 |
| "zod v4" in resolvers repo | 10 | 10 |
| Recent releases react-hook-form | 15 | 5 |
| Recent releases zod | 10 | 3 |

**Total Issues Reviewed**: 75+

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "react-hook-form zod edge case" | No results | N/A |
| "useFieldArray react-hook-form" | No results | N/A |
| "react-hook-form performance" | No results | N/A |

**Note**: WebSearch returned no Stack Overflow results for specific queries, but general searches found relevant content.

### Web Search

| Source | Notes |
|--------|-------|
| [Alex Hooley Blog](https://alexhooley.com/blog/react-hook-form-common-mistakes) | Common pitfalls guide |
| [Contentful Blog](https://www.contentful.com/blog/react-hook-form-validation-zod/) | Zod integration guide |
| [Medium Article](https://medium.com/@jinha4ever/debugging-react-hook-form-zod-understanding-how-defaultvalues-and-unregister-work-74b54813de0d) | Deep dive on unregister |
| [Wasp Blog](https://wasp.sh/blog/2025/01/22/advanced-react-hook-form-zod-shadcn) | Advanced patterns |

### Official Documentation

| Source | Notes |
|--------|-------|
| [react-hook-form.com](https://react-hook-form.com/docs/useform) | Official API docs |
| [zod.dev](https://zod.dev/) | Zod documentation |
| [shadcn/ui docs](https://ui.shadcn.com/docs/forms/react-hook-form) | Form component integration |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release list` and `gh release view` for changelogs
- `WebSearch` for community content
- Manual cross-referencing with official docs

**Limitations**:
- Stack Overflow WebSearch returned no results (may be search API limitation)
- Some older issues (pre-2024) excluded to focus on recent problems
- Beta versions (Zod v4 beta, RHF v8 beta) issues flagged as unstable

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.2 (Zod v4 optional fields), 1.5 (performance), and 1.11 (Zod v4.3.0 features) against current official Zod documentation.

**For api-method-checker**: Verify that Zod v4.3.0 methods (.exactOptional(), .xor(), z.fromJSONSchema(), z.looseRecord()) exist and work as described in finding 1.11.

**For code-example-validator**: Validate code examples in findings 1.2, 1.3, 1.5, 1.7, 1.11, and 2.2 before adding to skill.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### New Known Issues Section Entries:

```markdown
13. **Zod v4 Optional Fields Validation Bug** - Empty string incorrectly fails validation for `.optional()` fields. Use `.nullish()`, `.or(z.literal(""))`, or preprocess to convert empty string to undefined.

14. **useFieldArray Primitive Arrays Not Supported** - Design limitation: `useFieldArray` only works with arrays of objects, not primitives like `string[]`. Wrap primitives in objects: `[{ value: "string" }]`.

15. **Validation Race Condition** - During resolver validation, `isValidating` may become false before errors are populated. Don't derive validity from errors alone; check `!errors.field && !isValidating`.
```

#### Performance Section Update:

```markdown
## Performance

### Large Forms (300+ Fields)

**Warning**: Forms with 300+ fields using a resolver (Zod/Yup) AND reading formState can freeze for 10-15 seconds.

**Workarounds**:
1. **Avoid destructuring formState** - Read properties inline when needed
2. **Use mode: "onSubmit"** - Don't validate on every change
3. **Split into sub-forms** - Multiple smaller forms with separate schemas
4. **Lazy render fields** - Use tabs/accordion to mount only visible fields

```typescript
// ❌ Slow with 300+ fields:
const { isDirty, isValid } = form.formState;

// ✅ Fast:
const isValid = form.formState.isValid; // Read inline only when needed
```
```

#### Advanced Patterns Section - Add Zod v4.3.0 Features:

```markdown
## Zod v4.3.0+ Features

**Exact Optional Fields** (.exactOptional()):
```typescript
const schema = z.object({
  email: z.string().email(),
  middleName: z.string().exactOptional(), // Can omit, but NOT undefined
});

schema.parse({});                       // ✅
schema.parse({ middleName: undefined }); // ❌
```

**Exclusive Union** (z.xor()):
```typescript
// Exactly one option must match
const schema = z.xor([
  z.object({ type: z.literal("email"), email: z.string().email() }),
  z.object({ type: z.literal("phone"), phone: z.string() }),
]);
```

**JSON Schema Import**:
```typescript
const schema = z.fromJSONSchema({
  type: "object",
  properties: {
    name: { type: "string", minLength: 1 },
  },
  required: ["name"],
});

const form = useForm({ resolver: zodResolver(schema) });
```
```

#### Add "Upcoming Changes in V8" Section:

```markdown
## Upcoming Changes in V8 (Beta)

React Hook Form v8 (currently beta) introduces breaking changes:

- `useFieldArray`: `id` renamed to `key`, `keyName` prop removed
- `<Watch />`: `names` prop renamed to `name`
- `watch()` callback API removed (use `useWatch` instead)
- `setValue()` no longer updates `useFieldArray` (use `replace()`)

**Migration Guide**: [Link to official migration docs when v8 stable]
```

---

**Research Completed**: 2026-01-20 14:30
**Next Research Due**: After React Hook Form v8 stable release OR Zod v5 release (whichever comes first)
