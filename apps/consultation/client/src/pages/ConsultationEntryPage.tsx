import { ActionButton, SectionHeading, SurfaceCard } from "../components/patient-ui";

type ConsultationEntryPageProps = {
  loading: boolean;
  onStart: () => Promise<void>;
};

function ConsultationEntryPage({ loading, onStart }: ConsultationEntryPageProps) {
  return (
    <SurfaceCard className="p-6 md:p-8">
      <SectionHeading
        eyebrow="正式问诊入口"
        title="系统已自动绑定默认数字医生"
        description="当前患者资料已完善。下一步将创建规则版数字人问诊会话，并由系统在完成后自动切换到量表问诊阶段。"
      />

      <div className="mt-8 flex">
        <ActionButton disabled={loading} onClick={() => void onStart()}>
          进入正式问诊
        </ActionButton>
      </div>
    </SurfaceCard>
  );
}

export default ConsultationEntryPage;
