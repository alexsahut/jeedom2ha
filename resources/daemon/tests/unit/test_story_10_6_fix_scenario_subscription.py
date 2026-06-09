"""Story 10.6 — Fix: souscription MQTT manquante pour les commandes de scénario.

Vérifie que COMMAND_SUBSCRIPTION_TOPICS inclut le topic scenario afin que le
CommandSynchronizer reçoive bien les press events envoyés par HA.
"""

from transport.mqtt_client import COMMAND_SUBSCRIPTION_TOPICS


class TestScenarioCommandSubscription:
    """AC1 — Le daemon souscrit au topic de commande des scénarios."""

    def test_scenario_cmd_topic_in_subscriptions(self):
        assert "jeedom2ha/scenario_+/cmd" in COMMAND_SUBSCRIPTION_TOPICS

    def test_existing_topics_still_present(self):
        assert "jeedom2ha/+/set" in COMMAND_SUBSCRIPTION_TOPICS
        assert "jeedom2ha/+/brightness/set" in COMMAND_SUBSCRIPTION_TOPICS
        assert "jeedom2ha/+/position/set" in COMMAND_SUBSCRIPTION_TOPICS

    def test_subscription_count(self):
        # 3 topics existants + 1 ajouté par Story 10.6
        assert len(COMMAND_SUBSCRIPTION_TOPICS) == 4
