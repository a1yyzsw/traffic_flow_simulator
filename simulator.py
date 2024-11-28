import pygame
import random
import json

# Initialize Pygame
pygame.init()

# Global constants
LANE_HEIGHT = 40  # Height of each lane
FPS = 30          # Frames per second

# Color definitions
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GREY = (200, 200, 200)

# Vehicle class
class Vehicle:
    def __init__(self, id, lane, speed, acceleration, reaction_time, length, position):
        self.id = id
        self.lane = lane
        self.speed = speed
        self.acceleration = acceleration
        self.reaction_time = reaction_time
        self.length = length
        self.position = position  # Initial position
        self.color = random.choice([BLUE, BLACK, WHITE])

    def move(self, dt, speed_limit, road_length, vehicles_in_lane):
        self.speed = min(self.speed, speed_limit)  # Ensure speed does not exceed the speed limit
        front_vehicle = self.get_front_vehicle(vehicles_in_lane)
        if front_vehicle:
            safe_distance = self.speed * self.reaction_time + 2  # Calculate safe distance
            if front_vehicle.position - front_vehicle.length/2 - self.position - self.length/2 < safe_distance:
                self.speed = max(0, front_vehicle.speed - 1)  # Slow down to avoid collisions
            else:
                self.speed += self.acceleration
        else:
            self.speed += self.acceleration
        self.position += self.speed * dt

        # Check if the vehicle has exited the road
        if self.position > road_length:
            return True  # Indicate that the vehicle should be removed
        return False

    def get_front_vehicle(self, vehicles_in_lane):
        front_vehicles = [v for v in vehicles_in_lane if v.position > self.position]
        if front_vehicles:
            return min(front_vehicles, key=lambda v: v.position)
        return None

    def draw(self, screen):
        x = self.position
        y = self.lane * LANE_HEIGHT + 10
        pygame.draw.rect(screen, self.color, (x, y, self.length, 20))  # Draw vehicle as a rectangle

# Road class
class Road:
    def __init__(self, length, lanes, traffic_lights):
        self.length = length
        self.lanes = lanes
        self.traffic_lights = traffic_lights

    def draw(self, screen):
        pygame.draw.line(screen, BLACK, (0, 0), (self.length, 0), LANE_HEIGHT)
        for lane in range(1, self.lanes+1):
            pygame.draw.line(screen, WHITE, (0, lane * LANE_HEIGHT), (self.length, lane * LANE_HEIGHT), 2)

        for light in self.traffic_lights:
            x = light["position"]
            color = RED if light["state"] == "red" else GREEN
            pygame.draw.circle(screen, color, (x, 10), 10)
            # pygame.font.init()
            font = pygame.font.SysFont(pygame.font.get_default_font(), 50)
            countdown_text = font.render(str(light["time_remain"]), False, color)
            screen.blit(countdown_text, (x + 15, 5))

    def update_traffic_lights(self, time):
        for light in self.traffic_lights:
            r_d = light["red_duration"]
            g_d = light["green_duration"]
            cycle = r_d + g_d
            light["state"] = "red" if time % cycle < r_d else "green"
            light["time_remain"] = int(r_d - time % cycle) if light["state"] == "red" else int(g_d - time % cycle % r_d)

# Simulator class
class Simulator:
    def __init__(self, params):
        self.road = Road(params["road_length"], params["lane_count"], params["traffic_lights"])
        self.vehicles = self.initialize_vehicles(params)
        self.vehicle_count = params["vehicle_count"]
        self.time = 0

    def initialize_vehicles(self, params):
        vehicles = []
        for lane in range(self.road.lanes):
            lane_positions = self.generate_lane_positions(
                lane, params["road_length"], params["vehicle_count"] // self.road.lanes, params
            )
            for pos in lane_positions:
                vehicles.append(
                    Vehicle(
                        id=len(vehicles),
                        lane=lane,
                        speed=random.uniform(10, params["speed_limit"]),
                        acceleration = random.uniform(1,10),
                        reaction_time=random.uniform(*params["reaction_time_range"]),
                        length=random.randint(30, 60),
                        position=pos
                    )
                )
        return vehicles

    def generate_lane_positions(self, lane, road_length, vehicle_count, params):
        positions = []
        min_distance = 10
        for _ in range(vehicle_count):
            if positions:
                last_position = positions[-1]
                safe_distance = random.uniform(100, 150)
                new_position = last_position + safe_distance + random.randint(3, 6)
            else:
                new_position = random.randint(0, road_length // 4)

            if new_position + 6 < road_length:
                positions.append(new_position)

        return positions

    def update(self):
        self.time += 1 / FPS
        self.road.update_traffic_lights(self.time)

        for lane in range(self.road.lanes):
            vehicles_in_lane = [v for v in self.vehicles if v.lane == lane]

            for vehicle in vehicles_in_lane:
                if vehicle.move(1 / FPS, params["speed_limit"], self.road.length, vehicles_in_lane):
                    self.vehicles.remove(vehicle)

        if len(self.vehicles) < self.vehicle_count:
            self.spawn_vehicle()

    def spawn_vehicle(self):
        lane = random.randint(0, self.road.lanes - 1)
        vehicles_in_lane = [v for v in self.vehicles if v.lane == lane]

        if vehicles_in_lane:
            front_vehicle = min(vehicles_in_lane, key=lambda v: v.position)
            new_position = max(0, front_vehicle.position - random.uniform(100, 150) - random.randint(3, 6))
        else:
            new_position = 0

        new_vehicle = Vehicle(
            id=len(self.vehicles),
            lane=lane,
            speed=random.uniform(10, 40),
            acceleration = random.uniform(1,10),
            reaction_time=random.uniform(1.0, 2.5),
            length=random.randint(30, 60),
            position=new_position
        )
        self.vehicles.append(new_vehicle)

    def draw(self, screen):
        screen.fill(GREY)
        self.road.draw(screen)
        for vehicle in self.vehicles:
            vehicle.draw(screen)

# Load parameters from a JSON file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Main loop
def main():
    global params
    params = load_config("config.json")

    screen_width = params["road_length"]
    screen_height = (params["lane_count"] + 1) * LANE_HEIGHT
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Traffic Flow Simulator")

    simulator = Simulator(params)
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        simulator.update()
        simulator.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
