import { InterventionEmbeddedExperience } from "../features/intervention/InterventionEmbeddedExperience";
import { INTERVENTION_GAME_IFRAME_SRC } from "../features/intervention/embeddedExperiences";

export default function InterventionGamePage() {
  return (
    <InterventionEmbeddedExperience
      eyebrow="Interactive Game"
      title="心灵花园"
      subtitle="输入一个让你感到温暖或有力量的词语，让它在花园中绽放。"
      iframeSrc={INTERVENTION_GAME_IFRAME_SRC}
      openEvent={{
        event_type: "experience_opened",
        program_id: "mindbloom-word-garden",
        program_title: "心灵花园词语游戏",
        delivery_mode: "game",
        payload: { page: "intervention-game" },
      }}
    />
  );
}
