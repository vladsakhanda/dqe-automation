*** Settings ***
Documentation     Compares the "Last week loaded data" table of the HTML report
...               with the facility_type_avg_time_spent_per_visit_date Parquet dataset.
Library           SeleniumLibrary
Library           OperatingSystem
Library           helper.py
Test Teardown     Close Browser


*** Variables ***
${REPORT_FILE}         ${CURDIR}${/}report.html
${PARQUET_FOLDER}      ${CURDIR}${/}parquet_data${/}facility_type_avg_time_spent_per_visit_date
# Report shows the last 7 loaded days: last visit_date in Parquet minus 6 days.
# Leave empty to compare with the whole dataset.
${FILTER_DATE}         2026-11-19
${BROWSER}             chrome
${BROWSER_OPTIONS}     add_argument("--headless=new");add_argument("--window-size=1920,1080")
${TABLE_LOCATOR}       css:.table
${TIMEOUT}             20s


*** Test Cases ***
HTML Report Table Matches Parquet Dataset
    [Documentation]    Passes when the HTML table and the filtered Parquet data match exactly.
    Open Report In Browser    ${REPORT_FILE}
    Wait Until Element Is Visible    ${TABLE_LOCATOR}    timeout=${TIMEOUT}
    ${table}=    Get WebElement    ${TABLE_LOCATOR}
    ${html_df}=    Read Html Table    ${table}
    Log    HTML table:\n${html_df}
    ${parquet_df}=    Read Parquet Dataset    ${PARQUET_FOLDER}    ${FILTER_DATE}
    Log    Parquet data (visit_date >= ${FILTER_DATE}):\n${parquet_df}
    ${is_equal}    ${differences}=    Compare Dataframes    ${html_df}    ${parquet_df}
    Log    ${differences}
    Should Be True    ${is_equal}    msg=${differences}


*** Keywords ***
Open Report In Browser
    [Arguments]    ${file}
    File Should Exist    ${file}
    ${url}=    Evaluate    pathlib.Path($file).resolve().as_uri()    modules=pathlib
    Open Browser    ${url}    ${BROWSER}    options=${BROWSER_OPTIONS}
