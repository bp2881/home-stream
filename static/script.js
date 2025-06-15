fetch("/static/videos.json")
	.then((response) => response.json())
	.then((data) => {
		const container = document.getElementById("videoContainer");

		data.videos.forEach((video) => {
			const videoEl = document.createElement("video");
			videoEl.controls = true;
			videoEl.src = video;

			container.appendChild(videoEl);
		});
	})
	.catch((err) => {
		console.error("Failed to load video list:", err);
	});
