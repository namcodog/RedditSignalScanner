from app.services.semantic.layer_router import LayerRouter


def test_layer_router_maps_known_and_unknown_subreddits() -> None:
    router = LayerRouter(
        {
            "r/shopify": "L2",
            "r/amazonfba": "L2",
            "r/dropshipping": "L3",
        }
    )

    assert router.route("r/Shopify") == ("L2", "r/shopify")
    assert router.route("amazonfba") == ("L2", "r/amazonfba")
    assert router.route("r/unknownsub") == ("L1", "r/unknownsub")
