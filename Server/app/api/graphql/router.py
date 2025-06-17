from strawberry.fastapi import GraphQLRouter
from app.api.graphql.main_schema import schema # type: ignore

# Create Strawberry GraphQL router
graphql_router = GraphQLRouter(
    schema=schema,
    graphiql=True,  # enable GraphiQL interface
)
