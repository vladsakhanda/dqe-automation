import time
import os
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(BASE_DIR, "report.html")
OUTPUT_DIR = os.path.join(BASE_DIR, "results")

WAIT_TIMEOUT = 20
DOUGHNUT_COLUMNS = ["Facility Type", "Min Average Time Spent"]


class SeleniumWebDriverContextManager:
    """Creates a Chrome WebDriver on enter and always quits it on exit."""

    def __init__(self, headless: bool = True, window_size: str = "1920,1080"):
        self.headless = headless
        self.window_size = window_size
        self.driver: WebDriver | None = None

    def __enter__(self) -> WebDriver:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={self.window_size}")
        options.add_argument("--disable-gpu")
        try:
            self.driver = webdriver.Chrome(options=options)
        except WebDriverException as e:
            raise RuntimeError(f"Could not start Chrome WebDriver: {e.msg}") from e
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
        # Do not suppress exceptions raised inside the `with` block.
        return False


# --------------------------------------------------------------------------- #
# Table
# --------------------------------------------------------------------------- #
def extract_table(driver: WebDriver) -> pd.DataFrame:
    """Reads the Plotly table column by column and returns it as a DataFrame."""
    try:
        # Locator 1: XPath - wait until the table is rendered and visible.
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@class="table"]'))
        )
        # Locator 2: class name - table root and its columns.
        table = driver.find_element(By.CLASS_NAME, "table")
        columns = table.find_elements(By.CLASS_NAME, "y-column")
        if not columns:
            raise NoSuchElementException("Table has no columns (class 'y-column').")

        data = {}
        for column in columns:
            # Locator 3: ID - one header per column.
            header = column.find_element(By.ID, "header").text.strip()
            # Locator 4: CSS selector - data cells; header cell is excluded by its text.
            cells = column.find_elements(By.CSS_SELECTOR, "text.cell-text")
            data[header] = [c.text.strip() for c in cells if c.text.strip() != header]
    except TimeoutException as e:
        raise RuntimeError(f"Table did not become visible within {WAIT_TIMEOUT}s.") from e
    except NoSuchElementException as e:
        raise RuntimeError(f"Table element not found: {e.msg}") from e

    lengths = {h: len(v) for h, v in data.items()}
    if len(set(lengths.values())) != 1:
        raise RuntimeError(f"Table columns have different number of cells: {lengths}")
    return pd.DataFrame(data)


# --------------------------------------------------------------------------- #
# Doughnut chart
# --------------------------------------------------------------------------- #
def get_legend_items(driver: WebDriver):
    legend = driver.find_element(By.CLASS_NAME, "scrollbox")
    return legend.find_elements(By.CLASS_NAME, "traces")


def count_active_legend_items(driver: WebDriver) -> int:
    """A hidden (filtered-out) legend item is rendered with opacity 0.5."""
    return sum(1 for item in get_legend_items(driver)
               if float(item.value_of_css_property("opacity") or 1) == 1.0)


def get_slice_labels(driver: WebDriver):
    doughnut = driver.find_element(By.CLASS_NAME, "pielayer")
    return doughnut.find_elements(By.CSS_SELECTOR, "text.slicetext[data-notex='1']")


def extract_doughnut(driver: WebDriver) -> pd.DataFrame:
    rows = []
    for label in get_slice_labels(driver):
        tspans = label.find_elements(By.TAG_NAME, "tspan")
        if len(tspans) < 2:
            raise RuntimeError(f"Unexpected slice label format: {label.text!r}")
        rows.append([tspans[0].text.strip(), tspans[1].text.strip()])
    return pd.DataFrame(rows, columns=DOUGHNUT_COLUMNS)


def wait_for_doughnut(driver: WebDriver, expected_slices: int):
    """Waits until the chart shows one slice label per active legend item."""
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            lambda d: len(get_slice_labels(d)) == expected_slices
        )
    except TimeoutException as e:
        actual = len(get_slice_labels(driver))
        raise RuntimeError(
            f"Doughnut did not update: expected {expected_slices} slices, got {actual}."
        ) from e
    # Let the Plotly transition finish before the screenshot.
    time.sleep(0.5)


def save_state(driver: WebDriver, index: int):
    screenshot_path = os.path.join(OUTPUT_DIR, f"screenshot{index}.png")
    csv_path = os.path.join(OUTPUT_DIR, f"doughnut{index}.csv")
    if not driver.save_screenshot(screenshot_path):
        raise RuntimeError(f"Failed to save {screenshot_path}")
    df = extract_doughnut(driver)
    df.to_csv(csv_path, index=False)
    print(f"  screenshot{index}.png, doughnut{index}.csv -> {len(df)} slice(s)")


def process_doughnut(driver: WebDriver):
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pielayer"))
        )
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, "scrollbox"))
        )
    except TimeoutException as e:
        raise RuntimeError(f"Doughnut chart or its legend not found within {WAIT_TIMEOUT}s.") from e

    # Scroll the chart into view so it is on the screenshots.
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",
                          driver.find_element(By.CLASS_NAME, "pielayer"))

    # Stage 0: initial, unfiltered state.
    wait_for_doughnut(driver, count_active_legend_items(driver))
    save_state(driver, 0)

    # Stages 1..N: switch the filters off one by one. The last stage is the
    # edge case where every filter is unselected and the chart is empty.
    filter_names = [item.text.strip() for item in get_legend_items(driver)]
    for index, name in enumerate(filter_names, start=1):
        try:
            # Re-find items each time: Plotly re-renders the legend on click.
            item = next(i for i in get_legend_items(driver) if i.text.strip() == name)
            toggle = item.find_element(By.CSS_SELECTOR, "rect.legendtoggle")
            active_before = count_active_legend_items(driver)
            toggle.click()
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                lambda d: count_active_legend_items(d) == active_before - 1
            )
        except StopIteration as e:
            raise RuntimeError(f"Filter '{name}' disappeared from the legend.") from e
        except (NoSuchElementException, TimeoutException) as e:
            raise RuntimeError(f"Filter '{name}' could not be applied.") from e

        print(f"Filter {index}: '{name}' unselected")
        wait_for_doughnut(driver, count_active_legend_items(driver))
        if count_active_legend_items(driver) == 0:
            print("  edge case: all filters unselected, chart is empty")
        save_state(driver, index)


if __name__ == "__main__":
    if not os.path.isfile(REPORT_PATH):
        raise SystemExit(f"Report not found: {REPORT_PATH}. Copy it with "
                         f"`podman cp jenkins:/generated_report/report.html <path>`.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with SeleniumWebDriverContextManager() as driver:
        driver.get("file:///" + REPORT_PATH.replace(os.sep, "/"))

        table_df = extract_table(driver)
        table_df.to_csv(os.path.join(OUTPUT_DIR, "table.csv"), index=False)
        print(f"table.csv -> {len(table_df)} row(s), columns: {list(table_df.columns)}")

        print("Doughnut chart:")
        process_doughnut(driver)

    print(f"Done. Output: {OUTPUT_DIR}")
