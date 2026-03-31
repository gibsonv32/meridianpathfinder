# ==============================================================================
# Exercise 8.11 — Forecasting NZ Arrivals to Australia
# fpp3 Chapter 8
# ==============================================================================

library(fpp3)

# --- Part (a): Time Plot ---------------------------------------------------

nzarrivals <- aus_arrivals %>% filter(Origin == "NZ")

nzarrivals %>% autoplot(Arrivals) +
  labs(title = "Quarterly Arrivals to Australia from New Zealand",
       y = "Arrivals (thousands)")

# Description:
# - Clear upward trend from ~50k (early 1980s) to >100k (2012)
# - Strong quarterly seasonality with peaks in Q3 (NZ winter holidays)
# - Seasonal amplitude grows with level -> multiplicative seasonality
# - Dip around 2003 (possibly SARS-related)

# --- Part (b): Holt-Winters Multiplicative ---------------------------------

# Data ends 2012 Q3; remove last 2 years -> training ends 2010 Q3
train <- nzarrivals %>% filter(Quarter <= yearquarter("2010 Q3"))
test  <- nzarrivals %>% filter(Quarter > yearquarter("2010 Q3"))

hw_fit <- train %>%
  model(hw_mult = ETS(Arrivals ~ error("M") + trend("A") + season("M")))

hw_fc <- hw_fit %>% forecast(h = 8)

# Plot forecasts vs actuals
hw_fc %>%
  autoplot(nzarrivals, level = 80) +
  labs(title = "Holt-Winters Multiplicative Forecast vs Actuals",
       y = "Arrivals (thousands)")

# --- Part (c): Why Multiplicative? -----------------------------------------

# The seasonal fluctuations grow proportionally with the level of the series.
# An additive model assumes constant seasonal variation, which would be
# inappropriate here since peaks/troughs get larger as arrivals increase.

# --- Part (d): Four Models --------------------------------------------------

fit <- train %>%
  model(
    ets_auto = ETS(Arrivals),
    ets_bc   = ETS(box_cox(Arrivals, guerrero(Arrivals)) ~ error("A") + trend("A") + season("A")),
    snaive   = SNAIVE(Arrivals),
    stl      = decomposition_model(STL(log(Arrivals)), ETS(season_adjust))
  )

fc <- fit %>% forecast(h = 8)

# Print the fable
fc

# Plot all four models
fc %>%
  autoplot(nzarrivals, level = 80) +
  facet_wrap(~.model, ncol = 2, scales = "free_y") +
  labs(title = "Two-Year Forecasts from Four Models",
       y = "Arrivals (thousands)")

# --- Part (e): Accuracy and Residual Diagnostics ---------------------------

# Test set accuracy
accuracy(fc, nzarrivals) %>% arrange(RMSE)

# Residual plots for each model
fit %>% select(ets_auto) %>% gg_tsresiduals()
fit %>% select(ets_bc) %>% gg_tsresiduals()
fit %>% select(snaive) %>% gg_tsresiduals()
fit %>% select(stl) %>% gg_tsresiduals()

# Ljung-Box tests for each model
# ets_auto (MAM): 9 params -> dof = 8
# ets_bc (AAA on transformed): 9 params -> dof = 8
# snaive: 0 params -> dof = 0
# stl (ETS(A,A,N) on season_adjust): 4 params -> dof = 3

augment(fit) %>% filter(.model == "ets_auto") %>%
  features(.innov, ljung_box, lag = 16, dof = 8) %>% print()

augment(fit) %>% filter(.model == "ets_bc") %>%
  features(.innov, ljung_box, lag = 16, dof = 8) %>% print()

augment(fit) %>% filter(.model == "snaive") %>%
  features(.innov, ljung_box, lag = 8, dof = 0) %>% print()

augment(fit) %>% filter(.model == "stl") %>%
  features(.innov, ljung_box, lag = 8, dof = 3) %>% print()

# --- Part (f): Time Series Cross-Validation --------------------------------

# CV datasets: start with 36 observations, forecast 3 steps ahead
nz_cv <- nzarrivals %>%
  stretch_tsibble(.init = 36, .step = 1)

# Fit all four models on CV datasets
cv_fit <- nz_cv %>%
  model(
    ets_auto = ETS(Arrivals),
    ets_bc   = ETS(box_cox(Arrivals, guerrero(Arrivals)) ~ error("A") + trend("A") + season("A")),
    snaive   = SNAIVE(Arrivals),
    stl      = decomposition_model(STL(log(Arrivals)), ETS(season_adjust))
  )

cv_fc <- cv_fit %>% forecast(h = 3)

# CV accuracy comparison
cv_accuracy <- cv_fc %>% accuracy(nzarrivals)
cv_accuracy %>% arrange(RMSE)

# Visual comparison
cv_accuracy %>%
  select(.model, RMSE, MAE, MAPE) %>%
  pivot_longer(-`.model`, names_to = "Measure", values_to = "Value") %>%
  ggplot(aes(x = .model, y = Value, fill = .model)) +
  geom_col() +
  facet_wrap(~Measure, scales = "free_y") +
  labs(title = "Cross-Validation Accuracy Comparison",
       x = "Model", y = "Value") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
