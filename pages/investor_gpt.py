import os
import requests

from typing import Type
from pydantic import BaseModel, Field

import streamlit as st

from langchain.chat_models.openai import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.tools import BaseTool
from langchain.agents import initialize_agent, AgentType
from langchain.utilities import DuckDuckGoSearchAPIWrapper

openai_api_key = os.environ.get("OPENAI_API_KEY")

alpha_vantage_api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")

llm = ChatOpenAI(
    temperature=0.1,
    model_name="gpt-4o-mini",
    openai_api_key=openai_api_key,
)


class StockMarketSymbolSearchToolArgsSchema(BaseModel):
    query: str = Field(description="The query you will search for")


class StockMarketSymbolSearchTool(BaseTool):
    name = "StockMarketSymbolSearchTool"
    description = """
    Use this tool to find the stock market symbol for a company.
    It takes query as an argument.
    Example query: Stock Market Symbol for Apple Inc.
    """
    args_schema: Type[StockMarketSymbolSearchToolArgsSchema] = StockMarketSymbolSearchToolArgsSchema

    def _run(self, query):
        ddg = DuckDuckGoSearchAPIWrapper()
        return ddg.run(query)


class CompanyOverViewArgsSchema(BaseModel):
    symbol: str = Field(description="The stock symbol of the company. Example: AAPL, TSLA, etc.")


class CompanyOverViewTool(BaseTool):
    name = "CompanyOverView"
    description = """
    Use this tool to get an overview of the financials of the company.
    You should enter a stock symbol as an argument.
    """
    args_schema: Type[CompanyOverViewArgsSchema] = CompanyOverViewArgsSchema

    def _run(self, symbol):
        r = requests.get(
            f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={alpha_vantage_api_key}"
        )
        return r.json()


class CompanyIncomeStatementTool(BaseTool):
    name = "CompanyIncomeStatement"
    description = """
    Use this tool to get an income statement of a company.
    You should enter a stock symbol as an argument.
    """
    args_schema: Type[CompanyOverViewArgsSchema] = CompanyOverViewArgsSchema

    def _run(self, symbol):
        r = requests.get(
            f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey={alpha_vantage_api_key}"
        )
        return r.json()["annualReports"]


class CompanyStockPerformanceTool(BaseTool):
    name = "CompanyStockPerformance"
    description = """
    Use this tool to get the weekly performance of a company stock.
    You should enter a stock symbol as an argument.
    """
    args_schema: Type[CompanyOverViewArgsSchema] = CompanyOverViewArgsSchema

    def _run(self, symbol):
        r = requests.get(
            f"https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={symbol}&apikey={alpha_vantage_api_key}"
        )
        response = r.json()
        return list(response["Weekly Time Series"].items())[:200]


agent = initialize_agent(
    llm=llm,
    verbose=True,
    agent=AgentType.OPENAI_FUNCTIONS,
    handle_parsing_errors=True,
    tools=[
        StockMarketSymbolSearchTool(),
        CompanyOverViewTool(),
        CompanyIncomeStatementTool(),
        CompanyStockPerformanceTool(),
    ],
    agent_kwargs={
        "system_message": SystemMessage(
            content="""
            You are a hedge fund manager.
            
            You evaluate a company and provide your opinion and reasons why the stock is a buy or not.
            
            Consider the performance of a stock, the company overview and the income statement.
            
            Be assertive in your judgement and recommend the stock or advise the user against it.
            And You are GOOOD at Korean. so please translate the result to Korean.
        """
        )
    },
)

st.set_page_config(
    page_title="InvestorGPT",
    page_icon="💼",
)

st.markdown(
    """
    # InvestorGPT
            
    Welcome to InvestorGPT.
            
    Write down the name of a company and our Agent will do the research for you.
"""
)

company = st.text_input("Write the name of the company you are interested on.")

if company:
    result = agent.invoke(company)
    st.write(result["output"].replace("$", "\$"))
