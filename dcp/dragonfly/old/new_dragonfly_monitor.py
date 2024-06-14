# app.py, run with 'streamlit run app.py'
import os
import time
import pandas as pd
import streamlit as st

st.title("Dragonfly State")  # add a title

df = pd.read_csv("dfstate.csv")
st.write(df)
st.image("/tmp/guiding.png")

time.sleep(1)
st.rerun()
