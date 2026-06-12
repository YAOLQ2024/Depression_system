import { InterventionEmbeddedExperience } from "../features/intervention/InterventionEmbeddedExperience";
import { INTERVENTION_STORY_IFRAME_SRC } from "../features/intervention/embeddedExperiences";

export default function InterventionStoryPage() {
  return (
    <InterventionEmbeddedExperience
      eyebrow="Story Mode"
      title="听一段故事"
      subtitle="当前接入的是“小鹿和那片慢慢亮起来的森林”，点击画面即可开始互动与播放。"
      iframeSrc={INTERVENTION_STORY_IFRAME_SRC}
    />
  );
}
