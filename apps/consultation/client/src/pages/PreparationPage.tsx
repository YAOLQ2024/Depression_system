import type { FormEvent } from "react";

import { ActionButton, FormField, SectionHeading, SurfaceCard, TextArea, TextInput } from "../components/patient-ui";
import type { UserRecord } from "../types";

type PreparationPageProps = {
  user: UserRecord;
  loading: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

function PreparationPage({ user, loading, onSubmit }: PreparationPageProps) {
  const profile = user.profile || {};

  return (
    <SurfaceCard className="p-6 md:p-8">
      <SectionHeading
        eyebrow="问诊准备"
        title="填写基本信息"
        description="这些内容用于帮助系统更准确地组织问诊流程，并在后续量表与人工复核中提供背景参考。"
      />

      <form className="mt-8 grid gap-5 md:grid-cols-2" onSubmit={onSubmit}>
        <FormField label="姓名">
          <TextInput name="full_name" defaultValue={String(profile.full_name || user.full_name || "")} />
        </FormField>
        <FormField label="年龄">
          <TextInput name="age" defaultValue={String(profile.age || "")} />
        </FormField>
        <FormField label="身高(cm)">
          <TextInput name="height_cm" defaultValue={String(profile.height_cm || "")} />
        </FormField>
        <FormField label="体重(kg)">
          <TextInput name="weight_kg" defaultValue={String(profile.weight_kg || "")} />
        </FormField>
        <FormField label="婚姻状况">
          <TextInput name="marital_status" defaultValue={String(profile.marital_status || "")} />
        </FormField>
        <FormField label="父母婚姻状况">
          <TextInput name="parental_relationship" defaultValue={String(profile.parental_relationship || "")} />
        </FormField>
        <FormField label="父母职业">
          <TextInput name="parental_occupation" defaultValue={String(profile.parental_occupation || "")} />
        </FormField>
        <div className="hidden md:block" />
        <FormField className="md:col-span-2" label="既往就诊史">
          <TextArea name="prior_psychiatric_visit" defaultValue={String(profile.prior_psychiatric_visit || "")} />
        </FormField>
        <FormField className="md:col-span-2" label="家族史">
          <TextArea name="family_history" defaultValue={String(profile.family_history || "")} />
        </FormField>
        <div className="flex justify-end md:col-span-2">
          <ActionButton disabled={loading} type="submit">
            保存问诊准备信息
          </ActionButton>
        </div>
      </form>
    </SurfaceCard>
  );
}

export default PreparationPage;
