from typing import Optional, Union
from main.Component import SkillProvider
from main.Statement import OutputStatement
from app import fetch_inference_score, MeasureScoreResponse, M3QuestionnaireScoreResponse
import asyncio

class InferenceScoreSkillProvider(SkillProvider):
    def __init__(self, config):
        self.oauth_component = "your.authentication.component.path"
        super().__init__(config)

    async def get_inference_score(self, oauth, score_id: str) -> Union[MeasureScoreResponse, M3QuestionnaireScoreResponse]:
        # Fetch the inference score with the given scoreId
        inference_score = fetch_inference_score(oauth, score_id)

        while inference_score.state == "INIT":
            await asyncio.sleep(5)
            inference_score = fetch_inference_score(oauth, score_id)

        if inference_score.state == "FAIL":
            return "Inference score state is FAIL"

        if inference_score.type == "MLScore":
            return MeasureScoreResponse(
                requestId=inference_score.requestId,
                state=inference_score.state,
                id=inference_score.id,
                type=inference_score.type,
                score=inference_score.score,
                measure=inference_score.measure,
            )
        elif inference_score.type == "MultiScore":
            return M3QuestionnaireScoreResponse(
                requestId=inference_score.requestId,
                state=inference_score.state,
                id=inference_score.id,
                type=inference_score.type,
                score=inference_score.score,
                measure=inference_score.measure,
                functionalImpairment=inference_score.functionalImpairment,
                subScore=inference_score.subScore,
            )

        return "Unsupported inference score state"

    def on_execute(self, binder, user_id, package, data, **kwargs):
        score_id = data.get("scoreId")
        oauth = self.get_provider(self.oauth_component, package, user_id).oauth()
        result = asyncio.run(self.get_inference_score(oauth, score_id))

        output = OutputStatement(user_id)
        output.append_text(result)
        binder.post_message(output)

    def on_search(self, binder, user_id, package, data, query, **kwargs):
        pass
