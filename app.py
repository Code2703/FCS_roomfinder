import streamlit as st
import pandas as pd

st.write("this is yet another test")

my_df = pd.DataFrame({'x':[1], 'y':[2]})
my_df.set_index(None)

my_df

print(my_df)