fetch("/static/videos.json")
	.then((res) => res.json())
	.then((data) => {
		const grid = document.getElementById("movieGrid");

		data.videos.forEach((videoPath) => {
			const fileName = videoPath.split("/").pop();
			const displayName = decodeURIComponent(
				fileName.replace(".mp4", "").replace(/[_-]/g, " ")
			);

			const card = document.createElement("div");
			card.className = "card";

			const video = document.createElement("video");
			video.src = videoPath;
			video.controls = false;
			video.muted = true;
			video.preload = "metadata";
			video.playsInline = true;

			// On click, redirect to player
			card.onclick = () => {
				window.location.href = `/${encodeURIComponent(fileName)}`;
			};

			const title = document.createElement("div");
			title.className = "title";
			title.textContent = displayName;

			card.appendChild(video);
			card.appendChild(title);
			grid.appendChild(card);
		});
	})
	.catch((err) => {
		console.error("Error loading videos:", err);
	});
