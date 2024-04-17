import numpy as np
import pandas as pd
def calculate_performance(df, risk_free_rate=0.02):
    """
    计算投资组合和对标指数的表现指标，以及投资组合的超额表现。

    参数:
    - df: DataFrame，包含日期、投资组合每日净值、对标指数的列。
    - risk_free_rate: float，年化无风险利率，默认值为0.02。

    返回:
    - 两个字典，分别包含投资组合和对标指数的表现指标，以及投资组合的超额表现指标。
    """
    # 计算日收益率
    df['Portfolio_Returns'] = df['Portfolio'].pct_change()
    df['Index_Returns'] = df['Index'].pct_change()
    df['Excess_Returns'] = df['Portfolio_Returns'] - df['Index_Returns']

    # 年化收益率
    annualized_return_portfolio = (1 + df['Portfolio_Returns'].mean()) ** 252 - 1
    annualized_return_index = (1 + df['Index_Returns'].mean()) ** 252 - 1

    # 波动率
    volatility_portfolio = df['Portfolio_Returns'].std() * np.sqrt(252)
    volatility_index = df['Index_Returns'].std() * np.sqrt(252)
    volatility_excess = df['Excess_Returns'].std() * np.sqrt(252)

    # 夏普比率
    sharpe_ratio_portfolio = (annualized_return_portfolio - risk_free_rate) / volatility_portfolio
    sharpe_ratio_index = (annualized_return_index - risk_free_rate) / volatility_index

    # 最大回撤
    def max_drawdown(return_series):
        wealth_index = 1000 * (1 + return_series).cumprod()
        previous_peaks = wealth_index.cummax()
        drawdowns = (wealth_index - previous_peaks) / previous_peaks
        return drawdowns.min()

    max_drawdown_portfolio = max_drawdown(df['Portfolio_Returns'])
    max_drawdown_index = max_drawdown(df['Index_Returns'])

    # 贝塔系数
    cov_matrix = np.cov(df['Portfolio_Returns'][1:], df['Index_Returns'][1:])
    beta = cov_matrix[0, 1] / cov_matrix[1, 1]

    # 阿尔法值
    alpha = annualized_return_portfolio - (risk_free_rate + beta * (annualized_return_index - risk_free_rate))

    # 组织结果
    portfolio_indicators = {
        'Annualized Return': annualized_return_portfolio,
        'Volatility': volatility_portfolio,
        'Sharpe Ratio': sharpe_ratio_portfolio,
        'Max Drawdown': max_drawdown_portfolio,
        'Beta': beta,
        'Alpha': alpha
    }

    index_indicators = {
        'Annualized Return': annualized_return_index,
        'Volatility': volatility_index,
        'Sharpe Ratio': sharpe_ratio_index,
        'Max Drawdown': max_drawdown_index
    }

    excess_indicators = {
        'Excess Return': annualized_return_portfolio - annualized_return_index,
        'Excess Volatility': volatility_excess,
        'Information Ratio': (annualized_return_portfolio - annualized_return_index) / volatility_excess
    }

    return portfolio_indicators, index_indicators, excess_indicators


def calculate_and_export_cumulative_return_probabilities(df):
    """
    基于年累计、月累计和周累计的收益率，计算策略和指数的正收益率概率，并将结果导出到DataFrame。

    参数:
    - df: DataFrame，包含日期、投资组合每日净值、对标指数的列。

    返回:
    - 一个DataFrame，包含策略、指数的正收益率概率以及策略的正超额收益率概率。
    """
    # 准备数据，计算日收益率
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df['Portfolio_Returns'] = df['Portfolio'].pct_change()
    df['Index_Returns'] = df['Index'].pct_change()

    # 计算累计收益率
    def calculate_cumulative_returns(df, freq):
        return df.resample(freq).apply(lambda x: (1 + x).prod() - 1)

    # 初始化结果DataFrame
    results_df = pd.DataFrame(
        columns=['Frequency', 'Portfolio Positive Return Probability', 'Index Positive Return Probability',
                 'Excess Positive Return Probability'])

    # 定义周期
    frequencies = ['D','W', 'M', 'Y']

    for freq in frequencies:
        # 计算周期累计收益率
        portfolio_cum_returns = calculate_cumulative_returns(df['Portfolio_Returns'], freq)
        index_cum_returns = calculate_cumulative_returns(df['Index_Returns'], freq)
        excess_returns = portfolio_cum_returns - index_cum_returns

        # 计算正收益和正超额收益的概率
        portfolio_pos_return_prob = portfolio_cum_returns[
                                        portfolio_cum_returns > 0].count() / portfolio_cum_returns[portfolio_cum_returns!=0].count()
        index_pos_return_prob = index_cum_returns[index_cum_returns > 0].count() / index_cum_returns[index_cum_returns!=0].count()
        excess_pos_return_prob = excess_returns[excess_returns > 0].count() / excess_returns[excess_returns!=0].count()

        # 将结果添加到DataFrame
        results_df = pd.concat(results_df,pd.DataFrame([{'Frequency': freq,
                                        'Portfolio Positive Return Probability': portfolio_pos_return_prob,
                                        'Index Positive Return Probability': index_pos_return_prob,
                                        'Excess Positive Return Probability': excess_pos_return_prob}]),
                                       ignore_index=True)

    return results_df
