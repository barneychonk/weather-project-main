let weatherData = null;
let fahrenheit = false;
let range = 24;
const weatherDataUrl = new URL('weather-data.json', document.currentScript.src);

const byId = (id) => document.getElementById(id);
const temperature = (value) => {
	if (!Number.isFinite(value)) return '--';
	const converted = fahrenheit ? value * 9 / 5 + 32 : value;
	return Math.round(converted);
};
const valueOrDash = (value, digits = 0) => (
	Number.isFinite(value) ? Number(value).toFixed(digits) : '--'
);
const formatTime = (time) => time ? time.slice(11, 16) : '--:--';
const formatDate = (time) => {
	if (!time) return 'Weather for Seri Iskandar';
	const [year, month, day] = time.slice(0, 10).split('-').map(Number);
	return new Date(year, month - 1, day).toLocaleDateString(undefined, {
		weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
	});
};
const iconFor = (forecast) => {
	if (!forecast) return '🌡️';
	const probability = forecast.rain_prob == null ? 0 : forecast.rain_prob;
	const rainfall = forecast.rainfall == null ? 0 : forecast.rainfall;
	if (probability >= 60 || rainfall >= 0.5) return '🌧️';
	if (probability >= 30 || rainfall > 0) return '🌦️';
	return '☀️';
};
const weatherType = (observation, forecast) => {
	const rain = (observation && Number(observation.rainfall) > 0)
		|| (forecast && (Number(forecast.rainfall) > 0
			|| Number(forecast.rain_prob) >= 50));
	if (rain) return 'rain';

	const hasCloudCover = (value) => value != null && Number.isFinite(Number(value));
	const cloudCover = observation && hasCloudCover(observation.cloud_cover)
		? Number(observation.cloud_cover)
		: forecast && hasCloudCover(forecast.cloud_cover)
			? Number(forecast.cloud_cover)
			: null;
	return cloudCover !== null && cloudCover >= 50 ? 'cloudy' : 'clear';
};

function renderHourly(forecasts) {
	const upcoming = forecasts
		.filter((item) => item.lead <= 24)
		.filter((item, index) => index === 0 || item.lead % 3 === 0)
		.slice(0, 8);

	byId('hourly').innerHTML = upcoming.length
		? upcoming.map((item) => `
			<div class="hour">
				<small>${formatTime(item.time)}</small>
				<span class="sun">${iconFor(item)}</span>
				<strong>${temperature(item.temperature)}°</strong>
			</div>
		`).join('')
		: '<p class="empty-state">No upcoming forecast data.</p>';
}

function renderDays(forecasts) {
	const grouped = new Map();
	forecasts.forEach((item) => {
		const date = item.time.slice(0, 10);
		if (!grouped.has(date)) grouped.set(date, []);
		grouped.get(date).push(item);
	});

	const days = Array.from(grouped.entries());
	const allTemps = [];
	days.forEach(([, items]) => items.forEach((item) => {
		if (Number.isFinite(item.temperature)) allTemps.push(item.temperature);
	}));
	const rangeMax = allTemps.length ? Math.max(...allTemps) : 1;
	const rangeMin = allTemps.length ? Math.min(...allTemps) : 0;
	byId('days').innerHTML = days.length
		? days.map(([date, items], index) => {
			const temps = items.map((item) => item.temperature).filter(Number.isFinite);
			const high = temps.length ? Math.max(...temps) : null;
			const low = temps.length ? Math.min(...temps) : null;
			const start = Math.max(0, ((low - rangeMin) / (rangeMax - rangeMin || 1)) * 100);
			const width = Math.max(8, ((high - low) / (rangeMax - rangeMin || 1)) * 100);
			const dateParts = date.split('-').map(Number);
			const label = index === 0 ? 'Today' : new Date(
				dateParts[0], dateParts[1] - 1, dateParts[2]
			).toLocaleDateString(undefined, { weekday: 'short' });
			return `
				<div class="day">
					<small>${label}</small>
					<span class="weather">${iconFor(items[0])}</span>
					<div class="bar"><i style="left: ${start}%; width: ${width}%"></i></div>
					<b>${temperature(high)}° / <small>${temperature(low)}°</small></b>
				</div>
			`;
		}).join('')
		: '<p class="empty-state">No forecast data available.</p>';
}

function renderInsights(forecasts, analysis) {
	const temperatures = forecasts
		.filter((item) => item.lead <= 24 && Number.isFinite(item.temperature));
	if (temperatures.length) {
		const peak = temperatures.reduce((highest, item) =>
			item.temperature > highest.temperature ? item : highest
		);
		byId('temperatureInsightTitle').textContent = 'Warmest in the next 24 hours';
		byId('temperatureInsight').textContent =
			`${temperature(peak.temperature)}°${fahrenheit ? 'F' : 'C'} around ${formatTime(peak.time)}.`;
	}

	const nextSix = forecasts.filter((item) => item.lead <= 6);
	const rainChance = nextSix.reduce((highest, item) =>
		Math.max(highest, Number.isFinite(item.rain_prob) ? item.rain_prob : 0), 0
	);
	byId('rainInsightTitle').textContent =
		rainChance >= 50 ? 'Rain is likely soon' : 'Rain outlook for the next 6 hours';
	byId('rainInsight').textContent = nextSix.length
		? `Highest hourly rain probability: ${Math.round(rainChance)}%.`
		: 'No near-term forecast data available.';

	const overall = analysis && analysis.overall ? analysis.overall : {};
	const temperatureMetrics = overall.temperature || {};
	const tempMae = temperatureMetrics.mae;
	byId('verificationInsight').textContent = Number.isFinite(tempMae)
		? `Temperature forecast MAE: ${tempMae}°C across ${analysis.matched_pairs || 0} matched forecast/observation pairs (updated ${analysis.generated_at || 'unknown'}).`
		: 'No analysis results available yet. Run analyze.py to generate them.';
}

function draw() {
	const canvas = byId('chart');
	const rect = canvas.getBoundingClientRect();
	const pixelRatio = window.devicePixelRatio || 1;
	canvas.width = Math.max(1, Math.round(rect.width * pixelRatio));
	canvas.height = Math.max(1, Math.round(rect.height * pixelRatio));

	const context = canvas.getContext('2d');
	context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
	const width = rect.width;
	const height = rect.height;
	const padding = { left: 42, right: 12, top: 15, bottom: 28 };
	context.clearRect(0, 0, width, height);

	const forecasts = (weatherData && weatherData.forecasts ? weatherData.forecasts : [])
		.filter((item) => item.lead <= range && Number.isFinite(item.temperature));
	if (!forecasts.length || width === 0 || height === 0) {
		context.fillStyle = '#90a8c6';
		context.font = '13px Arial';
		context.fillText('No forecast data available.', padding.left, height / 2);
		return;
	}

	const temps = forecasts.map((item) => item.temperature);
	const minimum = Math.floor(Math.min(...temps) - 2);
	const maximum = Math.ceil(Math.max(...temps) + 2);
	const plotHeight = height - padding.top - padding.bottom;
	const plotWidth = width - padding.left - padding.right;
	const xAt = (index) => padding.left + index * plotWidth / Math.max(1, forecasts.length - 1);
	const yAt = (value) => padding.top + (maximum - value) * plotHeight / (maximum - minimum || 1);

	context.strokeStyle = 'rgba(148, 174, 208, 0.18)';
	context.lineWidth = 1;
	context.fillStyle = '#9aa8bc';
	context.font = '10px Arial';
	for (let index = 0; index < 5; index += 1) {
		const y = padding.top + plotHeight * index / 4;
		const value = maximum - (maximum - minimum) * index / 4;
		context.beginPath();
		context.moveTo(padding.left, y);
		context.lineTo(width - padding.right, y);
		context.stroke();
		context.fillText(`${temperature(value)}°`, 5, y + 3);
	}

	const rainMax = Math.max(0.1, ...forecasts.map((item) =>
		Number.isFinite(item.rainfall) ? item.rainfall : 0
	));
	const barWidth = Math.max(2, Math.min(8, plotWidth / forecasts.length * 0.55));
	forecasts.forEach((item, index) => {
		const rain = Number.isFinite(item.rainfall) ? item.rainfall : 0;
		const barHeight = rain / rainMax * plotHeight * 0.28;
		context.fillStyle = 'rgba(89, 215, 213, 0.55)';
		context.fillRect(xAt(index) - barWidth / 2, height - padding.bottom - barHeight, barWidth, barHeight);
	});

	context.strokeStyle = '#7dc8ff';
	context.lineWidth = 3;
	context.lineJoin = 'round';
	context.beginPath();
	forecasts.forEach((item, index) => {
		const x = xAt(index);
		const y = yAt(item.temperature);
		if (index === 0) context.moveTo(x, y);
		else context.lineTo(x, y);
	});
	context.stroke();

	const labelCount = Math.min(6, forecasts.length);
	context.fillStyle = '#99a6ba';
	context.font = '10px Arial';
	for (let index = 0; index < labelCount; index += 1) {
		const point = Math.round(index * (forecasts.length - 1) / Math.max(1, labelCount - 1));
		context.fillText(formatTime(forecasts[point].time), xAt(point) - 14, height - 7);
	}
}

function render() {
	if (!weatherData) {
		draw();
		return;
	}

	const forecasts = weatherData.forecasts || [];
	const current = weatherData.observation || forecasts[0] || {};
	const weather = weatherType(weatherData.observation, forecasts[0]);
	document.body.dataset.weather = weather;
	byId('weatherStatus').textContent = ({
		clear: 'CLEAR',
		cloudy: 'CLOUDY',
		rain: 'RAINY'
	})[weather];
	byId('date').textContent = formatDate(current.time);
	byId('updated').textContent = weatherData.updated_at
		? `Data through ${weatherData.updated_at.replace('T', ' ')} MYT`
		: 'Weather data timestamp unavailable';
	byId('currentTemp').innerHTML =
		`${temperature(current.temperature)}°<span>${fahrenheit ? 'F' : 'C'}</span>`;
	byId('condition').textContent = ({
		clear: 'Clear skies',
		cloudy: 'Cloudy',
		rain: 'Rainy conditions'
	})[weather];
	byId('weatherIcon').textContent = iconFor(forecasts[0]);
	byId('humidity').innerHTML = `${valueOrDash(current.humidity)}<small>%</small>`;
	byId('wind').innerHTML = `${valueOrDash(current.wind_speed)}<small> km/h</small>`;
	byId('rainChance').innerHTML =
		`${valueOrDash(forecasts[0] ? forecasts[0].rain_prob : undefined)}<small>%</small>`;
	byId('rainfall').innerHTML = `${valueOrDash(current.rainfall, 1)}<small> mm</small>`;

	renderHourly(forecasts);
	renderDays(forecasts.filter((item) => item.lead <= range));
	renderInsights(forecasts, weatherData.analysis);
	draw();
}

function loadWeather() {
	byId('updated').textContent = weatherData
		? 'Refreshing weather snapshot…'
		: 'Loading weather data…';
	fetch(weatherDataUrl, { cache: 'no-store' })
		.then((response) => {
			if (!response.ok) throw new Error(`Weather data returned HTTP ${response.status}`);
			return response.json();
		})
		.then((data) => {
			if (data.error) throw new Error(data.error);
			weatherData = data;
			render();
		})
		.catch((error) => {
			byId('updated').textContent = weatherData
				? 'Refresh failed — showing last snapshot'
				: 'Weather data unavailable';
			if (!weatherData) byId('weatherStatus').textContent = 'UNAVAILABLE';
			if (!weatherData) byId('condition').textContent = error.message;
		});
}

byId('unit').addEventListener('change', (event) => {
	fahrenheit = event.target.value === 'f';
	render();
});
byId('refresh').addEventListener('click', loadWeather);
document.querySelectorAll('.tabs button').forEach((button) => {
	button.addEventListener('click', () => {
		document.querySelectorAll('.tabs button').forEach((tab) => tab.classList.remove('active'));
		button.classList.add('active');
		range = Number(button.dataset.range);
		render();
	});
});
window.addEventListener('resize', draw);
loadWeather();
window.setInterval(loadWeather, 5 * 60 * 1000);
