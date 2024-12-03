import pygame
import random
import json

# Initialize Pygame
pygame.init()

# Load parameters from a JSON file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Global constants
global params
params = load_config("config.json")
SPEED_LIMIT = params["speed_limit"]
ROAD_LENGTH = params["road_length"]
LANE_COUNT = params["lane_count"]
LANE_WIDTH = params["lane_width"]
TRAFFIC_LIGHTS = params["traffic_lights"]
FPS = params["fps"]

# Color definitions
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GREY = (200, 200, 200)

# Vehicle class
class Vehicle:
    def __init__(self, id, lane, speed, max_acceleration, max_deceleration, reaction_time, speed_scale_preference, length, position):
        self.id = id
        self.lane = lane
        self.speed = speed                          # m/s
        self.max_acceleration = max_acceleration    # m/s^2
        self.max_deceleration = max_deceleration    # m/s^2
        self.reaction_time = reaction_time          # s
        self.speed_scale_preference = speed_scale_preference    # 0.5-1.5
        self.length = length                        # m
        self.position = position                    # [x, y, rotation], m m deg
        self.red_light_ahead = False
        self.color = WHITE

    def accelerate(self, value):
        self.speed = min(self.speed + min(value, self.max_acceleration), SPEED_LIMIT * self.speed_scale_preference)

    def brake(self, value):
        self.speed = max(self.speed - min(value, self.max_acceleration), 0)

    def slow_to_stop(self, value):
        while self.speed > 0:
            self.brake(value)

    def safe_distance(self):
        return self.speed * (self.reaction_time + self.speed / 10)
    
    def get_front_vehicle(self, vehicles_in_lane):
        front_vehicles = [v for v in vehicles_in_lane if v.position > self.position]
        if front_vehicles:
            return min(front_vehicles, key=lambda v: v.position)
        return None
    
    def front_distance(self, front_vehicle):
        if front_vehicle:
            return front_vehicle.position - self.position - front_vehicle.length/2 - self.length/2
        else:
            return float("inf")

    def watch_traffic_light(self):
        position_lights = [t["position"] for t in TRAFFIC_LIGHTS]
        position_lights.sort()
        for p_l in position_lights:
            if p_l <= self.position:
                continue
            if p_l - self.position < 200:
                self.red_light_ahead = True
                break
            else:
                self.red_light_ahead = False
                break
    
    def update_position(self, dt):
        self.position += self.speed * dt

    def change_lane(self, direction):
        if direction == "L":
            self.lane = max(self.lane - 1, 0)
        elif direction == "R":
            self.lane = min(self.lane + 1, LANE_COUNT - 1)
        else:
            print("invalid change lane input")

    def move(self, dt, speed_limit, road_length, vehicles_in_lane):
        self.speed = min(self.speed, speed_limit * self.speed_scale_preference)  # Ensure speed does not exceed the speed limit
        front_vehicle = self.get_front_vehicle(vehicles_in_lane)
        safe_distance = self.safe_distance()
        front_distance = self.front_distance(front_vehicle)

        if front_distance <= safe_distance:
            self.brake(abs(front_vehicle.speed - self.speed))  # Slow down to avoid collisions
        else:
            self.accelerate(1)

        self.update_position(dt)

        # Check if the vehicle has exited the road
        if self.position > road_length:
            return True  # Indicate that the vehicle should be removed
        return False



    def draw(self, screen):
        x = self.position
        y = (self.lane + 1) * LANE_WIDTH * 10 + LANE_WIDTH * 5
        pygame.draw.rect(screen, self.color, (x-self.length/2, y-10, self.length, 20), border_radius = 2)  # Draw vehicle as a rectangle
        font = pygame.font.SysFont(pygame.font.get_default_font(), 20)
        speed = font.render(str(int(self.speed * 3.6)), False, BLACK)
        screen.blit(speed, (x, y - 5))

# Road class
class Road:
    def __init__(self, length, lanes, traffic_lights):
        self.length = length
        self.lanes = lanes
        self.traffic_lights = traffic_lights

    def draw(self, screen):
        pygame.draw.line(screen, BLACK, (0, LANE_WIDTH * 10//2), (self.length, LANE_WIDTH * 10//2), LANE_WIDTH * 10)
        for lane in range(1, self.lanes+1):
            pygame.draw.line(screen, WHITE, (0, lane * LANE_WIDTH * 10), (self.length, lane * LANE_WIDTH * 10), 2)

        for light in self.traffic_lights:
            x = light["position"]
            color = RED if light["state"] == "red" else GREEN
            pygame.draw.circle(screen, color, (x, LANE_WIDTH * 10//2), 10)
            # pygame.font.init()
            font = pygame.font.SysFont(pygame.font.get_default_font(), 50)
            countdown_text = font.render(str(light["time_remain"]), False, color)
            screen.blit(countdown_text, (x + 15, 5))

    def update_traffic_lights(self, time):
        for light in self.traffic_lights:
            red_duration = light["red_duration"]
            green_duration = light["green_duration"]
            cycle = red_duration + green_duration
            light["state"] = "red" if time % cycle < red_duration else "green"
            light["time_remain"] = int(red_duration - time % cycle) if light["state"] == "red" else int(green_duration - time % cycle % red_duration)

# Simulator class
class Simulator:
    def __init__(self, params):
        self.road = Road(ROAD_LENGTH * 10, LANE_COUNT, TRAFFIC_LIGHTS)
        self.vehicles = self.initialize_vehicles(params)
        self.vehicle_count = params["vehicle_count"]
        self.time = 0

    def initialize_vehicles(self, params):
        vehicles = []
        for lane in range(self.road.lanes):
            lane_positions = self.generate_lane_positions(
                lane, ROAD_LENGTH * 10, params["vehicle_count"] // self.road.lanes, params
            )
            for pos in lane_positions:
                vehicles.append(
                    Vehicle(
                        id=len(vehicles),
                        lane=lane,
                        speed=random.uniform(10, SPEED_LIMIT),
                        max_acceleration = random.uniform(1,10),
                        max_deceleration = random.uniform(1,10),
                        reaction_time=random.uniform(*params["reaction_time_range"]),
                        speed_scale_preference=random.normalvariate(1.1,0.2),
                        length=random.randint(30,60),
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
                if vehicle.move(1 / FPS, SPEED_LIMIT, self.road.length, vehicles_in_lane):
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
            max_acceleration = random.uniform(1,10),
            max_deceleration = random.uniform(1,10),
            reaction_time=random.uniform(1.0,2.5),
            speed_scale_preference=random.normalvariate(1.1,0.2),
            length=random.randint(30, 60),
            position=new_position
        )
        self.vehicles.append(new_vehicle)

    def draw(self, screen):
        screen.fill(GREY)
        self.road.draw(screen)
        for vehicle in self.vehicles:
            vehicle.draw(screen)


# Main loop
def main():
    

    screen_width = ROAD_LENGTH * 10
    screen_height = (LANE_COUNT + 1) * LANE_WIDTH * 10
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
