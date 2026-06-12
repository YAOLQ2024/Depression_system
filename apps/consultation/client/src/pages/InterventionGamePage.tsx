import { InterventionEmbeddedExperience } from "../features/intervention/InterventionEmbeddedExperience";
import { INTERVENTION_GAME_IFRAME_SRC } from "../features/intervention/embeddedExperiences";

export default function InterventionGamePage() {
  return (
    <InterventionEmbeddedExperience
      eyebrow="Interactive Game"
      title="玩一个小游戏"
      subtitle="当前接入的是呼吸节奏小游戏，点击画面里的开始按钮即可进入互动。"
      iframeSrc={INTERVENTION_GAME_IFRAME_SRC}
    />
  );
}
