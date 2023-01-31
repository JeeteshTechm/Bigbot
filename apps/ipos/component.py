import json
import threading

from contrib.keycloak import KeycloakController
from core.models import BotDelegate, HumanDelegate, User
from main import Log
import main.Component as component
import main.Node as node
from main.Statement import OutputStatement


class IPOSProviders(component.DataExchange):
    """Sends a list of the available provider's bots. The bots are selected based on the assigned
    groups.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot_delegates = []
        self.groups = [
            g.strip() for g in self.get_variable("ai.bigbot.ipos", "BOT_GROUPS").split(",")
        ]
        self.human_delegates = []

    def call(self, binder, operator_id, package, data, **kwargs):
        thread = threading.Thread(target=self.filter_users)
        thread.start()
        self.filter_bots()

        result = []
        for bot in self.bot_delegates:
            result.append({"context": 2, "text": bot.name, "value": bot.id})

        thread.join()
        for delegate in self.human_delegates:
            result.append(
                {"context": 1, "text": delegate.name, "value": [delegate.id, delegate.name]}
            )

        result.sort(key=lambda x: x["text"].lower())

        output = OutputStatement(operator_id)
        if len(result) == 0:
            output.append_text("No providers where found")
        else:
            selection_node = node.ListSelectionNode(result)
            output.append_node(selection_node)

        binder.post_message(output)

    def filter_bots(self):
        result = []
        bots = BotDelegate.objects.filter(classification=BotDelegate.DELEGATE_BOT)

        if self.groups:
            for b in bots:
                try:
                    groups = json.loads(b.groups)
                except:
                    groups = []

                if any(g in groups for g in self.groups):
                    result.append(b)
        else:
            result = list(bots)

        self.bot_delegates = result

    def filter_users(self):
        filtered_groups = []
        result = []
        users = []

        if self.groups:
            kc = KeycloakController.get_singleton()
            kc_groups = kc.keycloak_admin.get_groups()
            for group in kc_groups:
                if group["name"] in self.groups:
                    filtered_groups.append(group)

        for group in filtered_groups:
            group_members = kc.keycloak_admin.get_group_members(group["id"])
            for member in group_members:
                if member not in users:
                    users.append(member)

        for u in users:
            user = User.get_keycloak_user(u["id"])
            delegate = HumanDelegate.find(user)
            result.append(delegate)

        self.human_delegates = result
