def basic_activity_suggestion_msg(activity_details):
    message = f"""We are on an incredible journey toward achieving your goal of *{activity_details['goal_name']}*. 
Every step you take brings you closer to realizing this vision.\n
Today, you have the opportunity to make significant progress 
by addressing the task of *{activity_details['task_name']}*.\n
Right now, please focus on the activity of *{activity_details['step_name']}*.\n 
This is your chance to push forward, to put in the effort that will get you one step closer 
to your ultimate goal. \nRemember, every small action builds momentum, and each completed activity is a 
victory in itself.\n\nWould you like to go ahead and finish this small yet significant activity?
"""
    return message
