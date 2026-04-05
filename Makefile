.PHONY: init status lint sync heal bootstrap mcp verify

init:
	./install.sh

status:
	./cli/wikictl status

lint:
	./cli/wikictl lint

sync:
	./cli/wikictl sync

heal:
	./cli/wikictl heal

bootstrap:
	./scripts/bootstrap-local.sh

mcp:
	npm run mcp

verify:
	bash ./scripts/verify.sh
