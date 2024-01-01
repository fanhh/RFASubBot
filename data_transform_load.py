import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
import logging

"""

scheduled script for updates of the db with the new data periodically on cloud


"""

# Define a function to clean data
def clean_data(csv_file):
    df = pd.read_csv(csv_file, skiprows=1)
    teachers = df.loc[(df['Teacher?'] == True) & (df['Teacher Inactive'] == False),
                      ['First Name', 'Last Name', 'TFA/RFA Email', 'Slack ID (RFA)', 'Comp Sci A', 'Biology', 'Chemistry', 
                       'Physics 1/2', 'Physics C', 'Algebra 1', 'Geometry', 'Algebra 2', 'Precalculus', 'Calculus',
                       'SAT Math', 'SAT English', 'Essay Writing', 'ES/MS English', 'Microeconomics', 'Macroeconomics']]
    
    teachers['Teachers'] = teachers['First Name'] + " " + teachers['Last Name']
    test = teachers.drop(columns=['First Name', 'Last Name', 'TFA/RFA Email', 'Slack ID (RFA)'])
    teachers_melted = test.melt(id_vars='Teachers', var_name='Subject', value_name='Teaches')
    df_filtered = teachers_melted[teachers_melted['Teaches']]
    grouped = df_filtered.groupby('Subject')['Teachers'].apply(list).reset_index()
    
    return grouped

# Function to update MySQL database
def update_database(df, table_name, db_connection_string):
    engine = create_engine(db_connection_string)
    df.to_sql(table_name, con=engine, if_exists='replace', index=False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        # Clean data
        new_teachers = clean_data("data/Volunteer Database.csv")

        # Database connection string
        db_connection_string = 'mysql+mysqlconnector://username:password@host:port/dbname'

        # Update database
        update_database(new_teachers, 'teachers_table', db_connection_string)
        logging.info("Database update complete.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

