type ConsultationEntryPageProps = {
  loading: boolean;
  onStart: () => Promise<void>;
};

function ConsultationEntryPage({ loading, onStart }: ConsultationEntryPageProps) {
  return (
    <section className="content-card readiness-page">
      <div className="card-title-row">
        <div>
          <p className="eyebrow">正式问诊入口</p>
          <h2>系统已自动绑定默认数字医生</h2>
        </div>
      </div>

      <p className="readiness-copy">
        当前患者资料已完善，下一步将创建规则版数字人问诊会话，并由系统自动切换到量表问诊阶段。
      </p>

      <div className="readiness-actions">
        <button className="primary-button" disabled={loading} onClick={() => void onStart()} type="button">
          进入正式问诊
        </button>
      </div>
    </section>
  );
}

export default ConsultationEntryPage;
