const videoList = document.getElementById("videoList");
const player = document.getElementById("player");

fetch("videos.json")
  .then(res => res.json())
  .then(data => {
    data.videos.forEach(file => {
      const li = document.createElement("li");
      li.textContent = file;
      li.onclick = () => {
        player.src = `media/${file}`;
        player.play();
      };
      videoList.appendChild(li);
    });
  });
