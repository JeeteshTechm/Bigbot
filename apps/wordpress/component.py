import json
import threading
import typing

from django.template import Context, Template
import requests

from contrib.utils import append_url, fuzzy_search
from main import Log
import main.Component as component
import main.Node as node
from main.Statement import OutputStatement

from .icon import icon


def append_tax_query(tax_query, sub_query):
    existing = None
    index = 0
    taxonomy = sub_query["taxonomy"]

    for key in tax_query:
        try:
            current = int(key)
            if current > index:
                index = current + 1
        except:
            current = False

        if current:
            if tax_query[key]["taxonomy"] == taxonomy:
                existing = key

    if existing is not None:
        terms = tax_query[existing]["terms"]
        for item in sub_query["terms"]:
            if item not in terms:
                terms.append(item)
        tax_query[existing]["terms"] = terms
    else:
        index = str(index)
        tax_query[index] = sub_query

    return tax_query


def get_property(properties, key, default=None):
    for property in properties:
        if property["name"] == key:
            return property["value"]
    return default


def remove_from_state(binder, key):
    state = binder.on_load_state()
    if key in state.data:
        del state.data[key]
    binder.on_save_state(state.serialize())


def save_state(binder, key, value):
    state = binder.on_load_state()
    state.data[key] = value
    binder.on_save_state(state.serialize())


def shorten_content(content):
    words = content.split(" ")
    result = []
    count = 0
    for word in words:
        if count == 50:
            break
        if len(word) > 0:
            result.append(word)
            count += 1
    return " ".join(result) + "..."


class WordpressAPI:
    """Class to interact with the Bigbot-Wordpress integration plugin."""

    def __init__(self, key, secret, url):
        self.key = key
        self.secret = secret
        self.url = url

    @staticmethod
    def post(server: str, method: str, *params) -> typing.Union[dict, list]:
        """Sents a post request to the server.

        Args:
            server (str): Server's URL. Should include the HTTP protocol.
            method (str): Method to use in the request. See the Bigbot-Wordpress plugin
                documentation for more information.
            params (list): Paremeters required by the required. See the Bigbot-Wordpress plugin
                documentation for more information.

        Returns:
            The request's response.
        """
        data = {"id": None, "jsonrpc": "2.0", "method": method, "params": params}
        response = requests.post(append_url(server, "/wp-json/bigbot/v1/posts"), json=data)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def search(server: str, query: dict, string: str, full: bool = False, res={}) -> list:
        """Search for a string

        Args:
            server (str): Server's URL. Should include the HTTP protocol.
            query (dict): WP_Query. Must at least include the post_type.
            string (str): String to look for.
            full (bool): If results should also include meta and taxonomies.

        Returns:
            list: A list of posts sorted by the confidence.
        """
        data = {"id": None, "jsonrpc": "2.0", "method": "search", "params": [query, string, full]}
        response = requests.post(append_url(server, "/wp-json/bigbot/v1/posts"), json=data)
        response.raise_for_status()
        result = response.json()
        res["result"] = result
        return result


class SearchMeta(component.SkillProvider):
    """Returns a list of all possible values in a specific meta key. The meta key must be
    specified in the properties of an InputSkill block as:

        {
            "name": "query",
            "value": {"meta_key": "name_of_meta_key", ...extra fields}
        }

    When a meta key is selected the global query will be updated:

        {
            ...
            "meta_query": [
                ...
                {
                    "compare": "LIKE",
                    "key": "name_of_meta_key",
                    "value": "value_of_meta_key"
                }
            ]
        }
    """

    def __init__(self, config):
        super().__init__(config)
        self.server = self.get_variable("com.big.bot.wordpress", "WORDPRESS_SERVER")

    def on_execute(self, binder, user_id, package, data, statement, **kwargs):
        """Process user input, saves data into state, and moves to the next block"""
        categories = data.get("wp_tmp", [])
        found = None
        similarity = 0
        thread_result = {}
        thread = threading.Thread(
            target=WordpressAPI.search,
            args=[self.server, data.get("wp_query", {}), statement.text, True, thread_result],
        )
        thread.start()

        for meta in categories:
            if statement.input == meta["value"]:
                found = meta
                break
            tmp_similarity, _ = fuzzy_search(statement.text, meta["text"])
            if tmp_similarity > similarity:
                found = meta
                similarity = tmp_similarity

        if found is not None:
            wp_query = data.get("wp_query", {})
            meta_key = wp_query.get("meta_key")
            if meta_key is None:
                raise Exception("meta_key does not exist in wp_query")
            del wp_query["meta_key"]
            meta_query = wp_query.get("meta_query", [])
            meta_query.append(
                {
                    "compare": "LIKE",
                    "key": meta_key,
                    "value": found["value"],
                }
            )
            wp_query["meta_query"] = meta_query
            save_state(binder, "wp_query", wp_query)
            remove_from_state(binder, "wp_tmp")
            return True
        else:
            thread.join()
            posts = thread_result.get("result", [])
            if posts:
                output = OutputStatement(user_id)
                preview_node = node.PreviewNode(posts[0]["permalink"])
                output.append_node(preview_node)
                print("output =>", output)
                binder.post_message(output)

        return False

    def on_search(self, binder, user_id, package, data, query, **kwargs):
        """ """
        result = [node.SearchNode.wrap_cancel()]
        categories = data.get("wp_tmp")
        wp_query = {
            **data.get("wp_query", {}),
            **get_property(kwargs.get("properties", {}), "query", {}),
        }

        if categories is None:
            categories = WordpressAPI.post(self.server, "list_meta", wp_query)
            save_state(binder, "wp_tmp", categories)
            save_state(binder, "wp_query", wp_query)

        for meta in categories:
            if query.lower() in meta["text"].lower():
                result.append(node.SearchNode.wrap_text(meta["text"], meta["value"]))

        return result


class SearchPost(component.SkillProvider):
    """Looks for a string in a post title, content, meta keys, or taxonomies.

    The search can be restricted by setting a custom query in the properties of a InputSkill block:

        {
            "name": "query",
            "value": {
                "post_type": "job_listing",
                "meta_query": {...},
                "tax_query": {...}
            }
        }

    The query will be merged with the global query.

    Note: This Skill should be the last one in the query contruction chain.
    """

    def __init__(self, config):
        super().__init__(config)
        self.server = self.get_variable("com.big.bot.wordpress", "WORDPRESS_SERVER")

    def on_execute(self, binder, user_id, package, data, statement, **kwargs):
        found = None
        posts = data.get("wp_tmp", [])
        similarity = 0
        thread_result = {}
        thread = threading.Thread(
            target=WordpressAPI.search,
            args=[self.server, data.get("wp_query", {}), statement.text, True, thread_result],
        )
        thread.start()

        for post in posts:
            if statement.input == post["ID"]:
                found = post
                break
            tmp_similarity, _ = fuzzy_search(statement.text, post["post_title"])
            if tmp_similarity > similarity:
                found = post
                similarity = tmp_similarity

        if found is not None:
            remove_from_state(binder, "wp_extra")
            remove_from_state(binder, "wp_query")
            remove_from_state(binder, "wp_tmp")
            preview_node = node.PreviewNode(found["permalink"])
            output = OutputStatement(user_id)
            output.append_node(preview_node)
            binder.post_message(output)
            return True
        else:
            thread.join()
            posts = thread_result.get("result", [])
            if posts:
                output = OutputStatement(user_id)
                preview_node = node.PreviewNode(posts[0]["permalink"])
                output.append_node(preview_node)
                print("output =>", output)
                binder.post_message(output)

        return False

    def on_search(self, binder, user_id, package, data, query, **kwargs):
        result = [node.SearchNode.wrap_cancel()]
        posts = data.get("wp_tmp")
        wp_query = {
            **data.get("wp_query", {}),
            **get_property(kwargs.get("properties", {}), "query", {}),
        }

        if posts is None:
            posts = WordpressAPI.post(self.server, "list_posts", wp_query, True)
            save_state(binder, "wp_tmp", posts)
            save_state(binder, "wp_query", wp_query)

        for post in posts:
            found = False
            if query.lower() in post["post_title"].lower():
                found = True
            elif query.lower() in post["post_content"].lower():
                found = True

            if not found:
                for key in post["meta"]:
                    meta = post["meta"][key]
                    for value in meta:
                        if query.lower() in value.lower():
                            found = True
                            break

            if not found:
                for taxonomy in post["taxonomies"]:
                    if query.lower() in taxonomy["name"].lower():
                        found = True
                        break

            if found:
                result.append(node.SearchNode.wrap_text(post["post_title"], post["ID"]))

        return result


class SearchTaxonomy(component.SkillProvider):
    """Returns a list of all possible values in a specific taxonomy. The taxonomy must be
    specified in the properties of an InputSkill block as:

        {
            "name": "query",
            "value": {"taxonomy": "name_of_taxonomy", ...extra fields}
        }

    When a meta key is selected the global query will be updated:

        {
            ...
            "tax_query": {
                "relation": "AND",
                ...
                "N": {
                    "fild": "term_id",
                    "operator": "IN",
                    "taxonomy": "name_of_taxonomy",
                    "terms": [..., term_id]
                }
            }
        }
    """

    def __init__(self, config):
        super().__init__(config)
        self.server = self.get_variable("com.big.bot.wordpress", "WORDPRESS_SERVER")

    def on_execute(self, binder, user_id, package, data, statement, **kwargs):
        """Process user input, saves data into state, and moves to the next block"""
        found = None
        similarity = 0
        taxonomies = data.get("wp_tmp", [])
        thread_result = {}
        thread = threading.Thread(
            target=WordpressAPI.search,
            args=[self.server, data.get("wp_query", {}), statement.text, True, thread_result],
        )
        thread.start()

        for tax in taxonomies:
            if statement.input == tax["term_id"]:
                found = tax
                break
            tmp_similarity, _ = fuzzy_search(statement.text, tax["name"])
            if tmp_similarity > similarity:
                found = tax
                similarity = tmp_similarity

        if found is not None:
            wp_query = data.get("wp_query", {})
            taxonomy = wp_query.get("taxonomy")
            if taxonomy is None:
                raise Exception("taxonomy does not exist in wp_query")
            del wp_query["taxonomy"]
            tax_query = append_tax_query(
                wp_query.get("tax_query", {"relation": "AND"}),
                {
                    "field": "term_id",
                    "operator": "IN",
                    "taxonomy": found["taxonomy"],
                    "terms": [found["term_id"]],
                },
            )
            wp_query["tax_query"] = tax_query
            save_state(binder, "wp_query", wp_query)
            remove_from_state(binder, "wp_tmp")
            return True
        else:
            thread.join()
            posts = thread_result.get("result", [])
            if posts:
                output = OutputStatement(user_id)
                preview_node = node.PreviewNode(posts[0]["permalink"])
                output.append_node(preview_node)
                print("output =>", output)
                binder.post_message(output)

        return False

    def on_search(self, binder, user_id, package, data, query, **kwargs):
        """ """
        result = [node.SearchNode.wrap_cancel()]
        taxonomies = data.get("wp_tmp")
        wp_query = {
            **data.get("wp_query", {}),
            **get_property(kwargs.get("properties", {}), "query", {}),
        }

        if taxonomies is None:
            taxonomies = WordpressAPI.post(self.server, "list_taxonomies", wp_query)
            save_state(binder, "wp_tmp", taxonomies)
            save_state(binder, "wp_query", wp_query)

        for taxonomy in taxonomies:
            if query.lower() in taxonomy["name"].lower():
                result.append(node.SearchNode.wrap_text(taxonomy["name"], taxonomy["term_id"]))

        return result


# class WordpressOAuthProvider(component.OAuthProvider):

#     def __init__(self, config):
#         super().__init__(config)
#         self.update_meta({
#             'icon': icon,
#             'title': 'Wordpress',
#             'description': 'You need to authorize your account first.',
#         })

#     def build_oauth(self, *args, **kwargs):
#         key = self.get_config().get('api_key')
#         secret = self.get_config().get('api_secret')
#         url = self.get_config().get('url')
#         return WordpressAPI(key, secret, url)


class WordpressProvider(component.SkillProvider):
    def on_execute(self, binder, user, package, data, *args, **kwargs):
        """Data is passed to processor"""
        Log.info(
            "WordpressProvider.on_execute",
            {
                "package": package,
                "data": data,
                "args": args,
                "kwargs": kwargs,
            },
        )
        if "error" in result:
            return
        return "I don't know"

    def on_search(self, binder, user, package, searchable, query, **kwargs):
        """Search for posts in this function"""
        model = searchable.property_value("model")
        oauth = self.oauth(binder, user, WordpressOAuthProvider)
        result = oauth.post(
            package=package, method="name_search", query=query, model=model, domain=[]
        ).json()["result"]

        items = []
        for item in result:
            items.append(
                self.create_text_search_item(
                    item["name"],
                    item["id"],
                )
            )
        return items
