IMAGE_NAME := ai-business-analyst
CONTAINER_NAME := ai-business-analyst-container

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run --network="host" \
		-v $(PWD)/src:/app \
		--name $(CONTAINER_NAME) \
		-it --rm $(IMAGE_NAME)

exec:
	docker exec -it $(CONTAINER_NAME) bash

clean:
	docker rmi -f $(IMAGE_NAME)

