import type { FormEvent } from "react";

import type { UserRecord } from "../types";

type PreparationPageProps = {
  user: UserRecord;
  loading: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

function PreparationPage({ user, loading, onSubmit }: PreparationPageProps) {
  const profile = user.profile || {};

  return (
    <section className="content-card">
      <div className="card-title-row">
        <div>
          <p className="eyebrow">问诊准备</p>
          <h2>填写基本信息</h2>
        </div>
      </div>

      <form className="prep-form" onSubmit={onSubmit}>
        <label>
          姓名
          <input name="full_name" defaultValue={String(profile.full_name || user.full_name || "")} />
        </label>
        <label>
          年龄
          <input name="age" defaultValue={String(profile.age || "")} />
        </label>
        <label>
          身高(cm)
          <input name="height_cm" defaultValue={String(profile.height_cm || "")} />
        </label>
        <label>
          体重(kg)
          <input name="weight_kg" defaultValue={String(profile.weight_kg || "")} />
        </label>
        <label>
          婚姻状况
          <input name="marital_status" defaultValue={String(profile.marital_status || "")} />
        </label>
        <label>
          父母婚姻状况
          <input name="parental_relationship" defaultValue={String(profile.parental_relationship || "")} />
        </label>
        <label>
          父母职业
          <input name="parental_occupation" defaultValue={String(profile.parental_occupation || "")} />
        </label>
        <label className="full-width">
          既往就诊史
          <textarea name="prior_psychiatric_visit" defaultValue={String(profile.prior_psychiatric_visit || "")} />
        </label>
        <label className="full-width">
          家族史
          <textarea name="family_history" defaultValue={String(profile.family_history || "")} />
        </label>
        <div className="form-actions full-width">
          <button className="primary-button" disabled={loading} type="submit">
            保存问诊准备信息
          </button>
        </div>
      </form>
    </section>
  );
}

export default PreparationPage;
