import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
from sklearn.model_selection import train_test_split
from statsmodels.stats.outliers_influence import variance_inflation_factor

def load_data(file_path: str, sheet_name: str, skip_rows: int) -> pd.DataFrame:
    """
    Load data from an Excel file.

    Parameters:
    - file_path (str): Path to the Excel file.
    - sheet_name (str): Name of the sheet containing the data.
    - skip_rows (int): Number of rows to skip at the beginning.

    Returns:
    - pd.DataFrame: Loaded DataFrame.
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)
    df = df.rename(columns={'Carat Weight': 'CaratWeight'})
    return df

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess the data by handling missing values and transforming features.

    Parameters:
    - df (pd.DataFrame): Original DataFrame.

    Returns:
    - pd.DataFrame: Preprocessed DataFrame.
    """

    # Replace values in the 'Clarity' column
    df['Clarity'] = df['Clarity'].replace({'IF': 'IF_FL', 'FL': 'IF_FL'})

    # Create a copy of the DataFrame for log transformation
    df_log = df.copy()

    # Log-transform 'Price' and 'CaratWeight'
    df_log['Price'] = df_log['Price'].transform(np.log)
    df_log['CaratWeight'] = df_log['CaratWeight'].transform(np.log)

    # One-hot encode 'Color' and 'Report' columns
    df_log = pd.get_dummies(data=df_log, columns=['Color', 'Report'], drop_first=True)

    # Define mapping scales for categorical features
    scale_map_cut = {'Fair': 1, 'Good': 2, 'Very Good': 3, 'Ideal': 4, 'Signature-Ideal': 5}
    scale_map_clarity = {'SI1': 1, 'VVS2': 3, 'VVS1': 3, 'VS2': 2, 'VS1': 2, 'IF_FL': 4}
    scale_map_polish = {'G': 1, 'VG': 2, 'EX': 3, 'ID': 3}

    # Replace values in categorical features using mapping scales
    df_log["Cut"] = df_log["Cut"].replace(scale_map_cut)
    df_log["Clarity"] = df_log["Clarity"].replace(scale_map_clarity)
    df_log["Polish"] = df_log["Polish"].replace(scale_map_polish)
    df_log["Symmetry"] = df_log["Symmetry"].replace(scale_map_polish)

    # Calculate Variance Inflation Factor (VIF) before data transformation
    vif_data = pd.DataFrame()
    vif_data["feature"] = df_log.drop(['Price', 'ID'], axis=1).columns
    vif_data["VIF"] = [variance_inflation_factor(
        df_log.drop(['Price', 'ID'], axis=1).values, i)
        for i in range(len(df_log.drop(['Price', 'ID'], axis=1).columns))]
    print("Previous VIF: \n", vif_data)

    # Mean centering numerical features
    df_log['CaratWeight'] = df_log['CaratWeight'] - df_log['CaratWeight'].mean()
    df_log['Cut'] = df_log['Cut'] - df_log['Cut'].mean()
    df_log['Polish'] = df_log['Polish'] - df_log['Polish'].mean()
    df_log['Symmetry'] = df_log['Symmetry'] - df_log['Symmetry'].mean()

    # Calculate VIF after data transformation
    vif_data = pd.DataFrame()
    vif_data["feature"] = df_log.drop(['Price', 'ID'], axis=1).columns
    vif_data["VIF"] = [variance_inflation_factor(
        df_log.drop(['Price', 'ID'], axis=1).values, i)
        for i in range(len(df_log.drop(['Price', 'ID'], axis=1).columns))]
    print("\n \n VIF after data transformation: \n", vif_data)

    # Create interaction terms for 'CaratWeight' and each color
    for color in ['E', 'F', 'G', 'H', 'I']:
        interaction_term = f'CaratWeight_color_{color}'
        df_log[interaction_term] = df_log['CaratWeight'] * df_log[f'Color_{color}']

    
    return df_log

def build_lm_model(X: pd.DataFrame, Y: pd.DataFrame) -> sm.regression.linear_model.RegressionResults:
    """
    Build a linear regression model.

    Parameters:
    - X (pd.DataFrame): Independent variables.
    - Y (pd.DataFrame): Dependent variable.

    Returns:
    - sm.regression.linear_model.RegressionResults: Linear regression model results.
    """
    X_const = sm.add_constant(X)
    lm = sm.OLS(Y, X_const).fit()
    return lm

def visualize_residual_plot(results: pd.DataFrame) -> None:
    """
    Visualize a residual plot.

    Parameters

:
    - results (pd.DataFrame): DataFrame containing model results and residuals.
    """
    fig = px.scatter(
        results, x='prediction_lm', y='residual_lm', height=350,
        labels={'prediction_lm': 'Predicted values using the Log Log Model', 'residual_lm': 'Residuals using the Log Log Model'}
    )
    fig.show()

def perform_cross_validation(X_train: pd.DataFrame, X_test: pd.DataFrame,
                              Y_train: pd.DataFrame, Y_test: pd.DataFrame) -> None:
    """
    Perform cross-validation.

    Parameters:
    - X_train (pd.DataFrame): Training set independent variables.
    - X_test (pd.DataFrame): Testing set independent variables.
    - Y_train (pd.DataFrame): Training set dependent variable.
    - Y_test (pd.DataFrame): Testing set dependent variable.
    """
    X_train_const = sm.add_constant(X_train)
    X_test_const = sm.add_constant(X_test)

    lm = sm.OLS(Y_train, X_train_const).fit()

    Y_pred = lm.predict(X_test_const)
    Y_pred_exp = np.exp(Y_pred)
    percent_errors = np.abs((np.exp(Y_test['Price']) - Y_pred_exp) / np.exp(Y_test['Price'])) * 100
    print("Log Log Model MAPE = ", np.mean(percent_errors), "%")

# Load data
file_path = "UV6248-XLS-ENG.xls"
sheet_name = "Raw Data"
skip_rows = 2
df = load_data(file_path, sheet_name, skip_rows)
final_test_data = df
df_dropped = df.dropna()

# Preprocess data
df_log = preprocess_data(df_dropped)
final_test_data_log=preprocess_data(final_test_data)


# Build LM Model
Y = df_log[(['Price'])]
X = df_log.drop(['Price', 'ID', 'Report_GIA'], axis=1)
lm_model = build_lm_model(X, Y)

# Display the summary of the model
print(lm_model.summary())

# Residual Plot
results_df = pd.DataFrame()
results_df['Price'] = df_log['Price']
results_df['prediction_lm'] = lm_model.fittedvalues
results_df['residual_lm'] = lm_model.resid

# Visualize Residual Plot
visualize_residual_plot(results_df)

# Cross Validation
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

perform_cross_validation(X_train, X_test, Y_train, Y_test)


# Use the trained model to predict the prices for the testing data. Call the vector of predicted prices Y_pred
X_test = final_test_data_log.drop(['Price','ID','Report_GIA'], axis=1)
X_test_const = sm.add_constant(X_test)
Y_pred = lm_model.predict(X_test_const)
Y_pred_exp = np.exp(Y_pred)
final_test_data['Predicted_Price']= Y_pred_exp
print('Predictions: \n\n',final_test_data)
final_test_data.to_csv("Sarah_gets_diamond_model_output.csv")