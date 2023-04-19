from rasa.core.channels.channel import InputChannel
from rasa.core.channels.channel import CollectingOutputChannel

class CustomConnector(InputChannel):
    @classmethod
    def name(cls) -> str:
        return "custom_connector"

    async def send_response(self, message: Dict[Text, Any], output) -> None:
        # Send the Rasa agent's response back to bigbot.
        output.append_text(message["text"])

    async def handle_message(self, agent: Agent, input, output, **kwargs: Any) -> None:
        # Pass the message from bigbot to the Rasa agent.
        output_channel = CollectingOutputChannel()
        await agent.handle_text(input.text, output_channel=output_channel)
        for message in output_channel.messages:
            await self.send_response(message, output)

    async def on_connect(self, input_channel: CustomConnector) -> None:
        # Handle any necessary setup when connecting bigbot to the Rasa agent.
        pass

    async def on_disconnect(self) -> None:
        # Handle any necessary cleanup when disconnecting bigbot from the Rasa agent.
        pass

    def process_utterance(self, statement):
        best_distance = 0.5
        best_match = None

        for utterance in DelegateUtterance.objects.all():
            match = textdistance.levenshtein.normalized_similarity(
                utterance.body.lower(), statement.text.lower()
            )
            if match > best_distance:
                best_distance = match
                best_match = utterance

        if best_match:
            delegates = best_match.human_delegates.all()
            groups = best_match.delegate_groups.all()
            return delegates, groups

        return None, None

    def on_standard_input(self, input, output):
        # Call the process_utterance method to find the best match for the input message.
        delegates, groups = self.process_utterance(input)

        if delegates or groups:
            # Handle the conversation routing according to the matched delegates and groups.
            pass
        else:
            # If no match is found, pass the input to the Rasa agent using the handle_message method.
            self.handle_message(input, output)
