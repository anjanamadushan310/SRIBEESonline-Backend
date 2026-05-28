# SRIBEESonline - Complete User Stories

> Detailed user stories for all 58 features across 10 EPICs

---

## 📑 Table of Contents

- [EPIC 1: User Authentication & Account Management](#epic-1-user-authentication--account-management)
- [EPIC 2: Product Catalog & Search](#epic-2-product-catalog--search)
- [EPIC 3: Shopping Cart & Wishlist](#epic-3-shopping-cart--wishlist)
- [EPIC 4: Checkout & Payment](#epic-4-checkout--payment)
- [EPIC 5: Order Management](#epic-5-order-management)
- [EPIC 6: Reviews & Ratings](#epic-6-reviews--ratings)
- [EPIC 7: Admin Dashboard](#epic-7-admin-dashboard)
- [EPIC 8: Notifications & Communication](#epic-8-notifications--communication)
- [EPIC 9: Advanced Watchlist Management](#epic-9-advanced-watchlist-management)
- [EPIC 10: Location-Based Branch Routing](#epic-10-location-based-branch-routing)

---

## EPIC 1: User Authentication & Account Management

### US-1.1: User Registration

**As a** new customer  
**I want to** register for an account with my email and password  
**So that** I can make purchases and track my orders

**Acceptance Criteria**:
- ✅ User can enter email, password, confirm password, and full name
- ✅ Email must be unique and in valid format
- ✅ Password must be at least 8 characters with 1 uppercase, 1 lowercase, 1 number, 1 special character
- ✅ Password strength indicator shows weak/medium/strong
- ✅ User must accept terms and conditions
- ✅ Verification email is sent after registration
- ✅ Account is inactive until email is verified
- ✅ User can resend verification email if not received
- ✅ Appropriate error messages for validation failures
- ✅ Success message displayed after registration

**Test Scenarios**:
1. Register with valid credentials → Success
2. Register with existing email → Error: "Email already exists"
3. Register with weak password → Error with strength requirements
4. Register without accepting terms → Error: "Must accept terms"
5. Verify email with valid token → Account activated
6. Verify email with expired token → Error with resend option

---

### US-1.2: User Login

**As a** registered customer  
**I want to** log in to my account securely  
**So that** I can access my profile, orders, and make purchases

**Acceptance Criteria**:
- ✅ User can enter email and password
- ✅ "Remember me" option extends session to 30 days
- ✅ Successful login redirects to homepage or intended page
- ✅ JWT access token (15 min) and refresh token (7 days) are issued
- ✅ Account locks for 15 minutes after 5 failed login attempts
- ✅ Clear error messages for invalid credentials
- ✅ Unverified accounts cannot log in
- ✅ Session persists across browser tabs
- ✅ User can log out from any page

**Test Scenarios**:
1. Login with valid credentials → Success, redirected to homepage
2. Login with invalid password → Error: "Invalid credentials"
3. Login with unverified email → Error: "Please verify your email"
4. 5 failed login attempts → Account locked for 15 minutes
5. Login with "Remember me" → Session persists for 30 days
6. Logout → Session cleared, redirected to homepage

---

### US-1.3: Social Login (Google/Facebook)

**As a** new or existing customer  
**I want to** log in using my Google or Facebook account  
**So that** I can quickly access the platform without creating a new password

**Acceptance Criteria**:
- ✅ "Continue with Google" button initiates OAuth flow
- ✅ "Continue with Facebook" button initiates OAuth flow
- ✅ New users are automatically registered on first social login
- ✅ Existing users can link social accounts to their profile
- ✅ User profile is populated with social account data (name, email, photo)
- ✅ Social login creates same session as regular login
- ✅ User can unlink social accounts from settings
- ✅ Error handling for OAuth failures

**Test Scenarios**:
1. First-time Google login → New account created, logged in
2. Existing user Google login → Logged in successfully
3. Link Google account to existing account → Successfully linked
4. Login with Facebook → OAuth flow completes, logged in
5. OAuth cancellation → User returned to login page
6. Unlink social account → Account unlinked, can still login with password

---

### US-1.4: Password Reset

**As a** customer who forgot my password  
**I want to** reset my password via email  
**So that** I can regain access to my account

**Acceptance Criteria**:
- ✅ User can request password reset by entering email
- ✅ Reset email sent only if email exists (no user enumeration)
- ✅ Reset link contains secure token valid for 1 hour
- ✅ User can set new password meeting strength requirements
- ✅ All existing sessions are invalidated after password reset
- ✅ User is redirected to login after successful reset
- ✅ Expired token shows error with option to request new link
- ✅ Used tokens cannot be reused

**Test Scenarios**:
1. Request reset with valid email → Email sent with reset link
2. Request reset with non-existent email → Generic success message (security)
3. Click valid reset link → Redirected to reset password form
4. Set new password → Success, all sessions invalidated
5. Click expired reset link → Error: "Link expired", option to resend
6. Reuse reset token → Error: "Invalid or expired token"

---

### US-1.5: Profile Management

**As a** logged-in customer  
**I want to** view and update my profile information  
**So that** my account details are current and accurate

**Acceptance Criteria**:
- ✅ User can view current profile (name, email, phone, profile picture)
- ✅ User can update full name and phone number
- ✅ User can upload/change profile picture (max 5MB, JPG/PNG)
- ✅ Profile picture is cropped to square and resized
- ✅ Email cannot be changed (security requirement)
- ✅ Changes are saved with confirmation message
- ✅ User can change password (requires current password)
- ✅ User can delete account with confirmation
- ✅ Account deletion is permanent and irreversible

**Test Scenarios**:
1. Update full name → Saved successfully
2. Upload profile picture → Image uploaded, cropped, displayed
3. Update phone number with invalid format → Error: "Invalid phone"
4. Change password with wrong current password → Error
5. Change password successfully → All sessions invalidated
6. Delete account → Confirmation modal, account deleted

---

### US-1.6: Address Management

**As a** logged-in customer  
**I want to** manage multiple delivery addresses  
**So that** I can easily ship orders to different locations

**Acceptance Criteria**:
- ✅ User can view all saved addresses
- ✅ User can add new address with full details
- ✅ User can edit existing addresses
- ✅ User can delete addresses (except default if only one)
- ✅ User can set one address as default
- ✅ Address types: Home, Work, Other
- ✅ Address validation for required fields
- ✅ Postal code validation
- ✅ Maximum 10 addresses per user

**Test Scenarios**:
1. Add new address → Address saved and displayed
2. Edit address → Changes saved successfully
3. Delete non-default address → Address removed
4. Set address as default → Default flag updated
5. Add 11th address → Error: "Maximum 10 addresses allowed"
6. Save address with invalid postal code → Error

---

### US-1.7: Two-Factor Authentication (2FA)

**As a** security-conscious customer  
**I want to** enable two-factor authentication  
**So that** my account has an extra layer of security

**Acceptance Criteria**:
- ✅ User can enable 2FA from security settings
- ✅ QR code generated for authenticator app (Google Authenticator, Authy)
- ✅ User must verify 6-digit code to enable 2FA
- ✅ 10 backup codes generated and displayed once
- ✅ User can download backup codes
- ✅ 2FA required on every login after enabling
- ✅ User can use backup code if authenticator unavailable
- ✅ User can disable 2FA (requires password + 2FA code)
- ✅ Used backup codes are marked as used

**Test Scenarios**:
1. Enable 2FA → QR code displayed, backup codes generated
2. Verify with correct code → 2FA enabled successfully
3. Login with 2FA enabled → Prompted for 6-digit code
4. Login with backup code → Success, code marked as used
5. Disable 2FA → Requires password and 2FA code
6. Login with wrong 2FA code → Error: "Invalid code"

---

## EPIC 2: Product Catalog & Search

### US-2.1: Browse Products by Category

**As a** customer  
**I want to** browse products organized by categories  
**So that** I can easily find products I'm interested in

**Acceptance Criteria**:
- ✅ Category menu displays all main categories
- ✅ Hovering over category shows subcategories
- ✅ Clicking category shows products in that category
- ✅ Breadcrumb navigation shows current category path
- ✅ Category page shows category image and description
- ✅ Product count displayed for each category
- ✅ Subcategories displayed on category page
- ✅ Empty categories show "No products available" message

**Test Scenarios**:
1. Click "Fruits & Vegetables" → Shows all products in category
2. Navigate to subcategory "Organic Vegetables" → Filtered products
3. Breadcrumb shows: Home > Fruits & Vegetables > Organic Vegetables
4. Category with no products → "No products available" message
5. Category menu shows product counts → Accurate counts displayed

---

### US-2.2: Search Products

**As a** customer  
**I want to** search for products by name or keyword  
**So that** I can quickly find specific products

**Acceptance Criteria**:
- ✅ Search bar visible on all pages
- ✅ Autocomplete suggestions appear as user types (min 2 characters)
- ✅ Suggestions include product names and categories
- ✅ Search results show relevant products
- ✅ Search highlights matching keywords
- ✅ "Did you mean?" suggestions for misspellings
- ✅ Search results can be filtered and sorted
- ✅ "No results" page with suggestions
- ✅ Search history saved for logged-in users

**Test Scenarios**:
1. Type "organic" → Autocomplete shows matching products
2. Search "organic milk" → Relevant results displayed
3. Search "orgnic" (misspelled) → "Did you mean organic?"
4. Search non-existent product → "No results found" with suggestions
5. View search history → Previous searches displayed
6. Clear search history → History removed

---

### US-2.3: Filter Products

**As a** customer  
**I want to** filter products by various attributes  
**So that** I can narrow down products to my preferences

**Acceptance Criteria**:
- ✅ Filter by price range (slider)
- ✅ Filter by brand (checkboxes)
- ✅ Filter by rating (4+ stars, 3+ stars, etc.)
- ✅ Filter by availability (In Stock, Out of Stock)
- ✅ Filter by attributes (Organic, Gluten-Free, etc.)
- ✅ Multiple filters can be applied simultaneously
- ✅ Active filters displayed as chips with remove option
- ✅ "Clear all filters" button
- ✅ Product count updates as filters are applied
- ✅ Filter state persists during session

**Test Scenarios**:
1. Set price range $10-$50 → Only products in range shown
2. Select "Organic" brand → Filtered to Organic brand
3. Apply multiple filters → Products match all criteria
4. Remove one filter → Results update accordingly
5. Clear all filters → All products shown again
6. No products match filters → "No products found" message

---

### US-2.4: Sort Products

**As a** customer  
**I want to** sort products by different criteria  
**So that** I can view products in my preferred order

**Acceptance Criteria**:
- ✅ Sort options: Relevance, Price (Low to High), Price (High to Low), Rating, Popularity, Newest
- ✅ Default sort is "Relevance" for search, "Popularity" for categories
- ✅ Sort dropdown visible on product listing pages
- ✅ Products re-order immediately on sort selection
- ✅ Sort preference persists during session
- ✅ Sort works with active filters
- ✅ Current sort option highlighted in dropdown

**Test Scenarios**:
1. Sort by "Price: Low to High" → Products ordered by ascending price
2. Sort by "Rating" → Highest rated products first
3. Sort by "Newest" → Recently added products first
4. Apply filter then sort → Both work together
5. Sort preference persists → Remains after page refresh

---

### US-2.5: View Product Details

**As a** customer  
**I want to** view detailed information about a product  
**So that** I can make an informed purchase decision

**Acceptance Criteria**:
- ✅ Product name, brand, and SKU displayed
- ✅ Image gallery with multiple product images
- ✅ Image zoom on hover/click
- ✅ Current price and original price (if discounted)
- ✅ Discount percentage badge
- ✅ Stock availability status (In Stock, Low Stock, Out of Stock)
- ✅ Product description (short and detailed)
- ✅ Product specifications/attributes table
- ✅ Customer reviews and average rating
- ✅ Related products section
- ✅ Add to cart and wishlist buttons
- ✅ Quantity selector
- ✅ Share buttons (Facebook, Twitter, WhatsApp)

**Test Scenarios**:
1. View product page → All details displayed correctly
2. Click product image → Zoom view opens
3. Navigate image gallery → All images viewable
4. Product out of stock → "Out of Stock" badge, cart button disabled
5. Click related product → Navigate to that product page
6. Share product → Share dialog opens

---

### US-2.6: Product Recommendations

**As a** customer  
**I want to** see recommended products  
**So that** I can discover products I might be interested in

**Acceptance Criteria**:
- ✅ "Frequently bought together" on product page
- ✅ "Customers also viewed" on product page
- ✅ "Similar products" based on category/attributes
- ✅ Personalized recommendations on homepage (logged-in users)
- ✅ "Trending products" section
- ✅ "New arrivals" section
- ✅ Recommendations update based on browsing history
- ✅ "Add all to cart" for bundle recommendations

**Test Scenarios**:
1. View product → "Frequently bought together" displayed
2. Browse multiple products → Personalized recommendations update
3. Homepage shows trending products → Displayed correctly
4. Click "Add all to cart" for bundle → All items added
5. New user → Generic recommendations shown

---

## EPIC 3: Shopping Cart & Wishlist

### US-3.1: Add Product to Cart

**As a** customer  
**I want to** add products to my shopping cart  
**So that** I can purchase them later

**Acceptance Criteria**:
- ✅ "Add to Cart" button on product listing and detail pages
- ✅ User can select quantity before adding
- ✅ Stock validation before adding to cart
- ✅ Success notification shows product added
- ✅ Mini cart preview updates with item count
- ✅ If product already in cart, quantity is updated
- ✅ Guest users can add to cart (session-based)
- ✅ Logged-in users have persistent cart
- ✅ Cart icon shows item count badge

**Test Scenarios**:
1. Add product to cart → Success notification, cart count updates
2. Add product already in cart → Quantity increases
3. Add product with insufficient stock → Error message
4. Add to cart as guest → Cart saved in session
5. Login after adding as guest → Guest cart merged with user cart
6. Add out of stock product → Button disabled

---

### US-3.2: View Shopping Cart

**As a** customer  
**I want to** view all items in my cart  
**So that** I can review my selections before checkout

**Acceptance Criteria**:
- ✅ Cart page lists all items with images
- ✅ Product name, price, quantity displayed for each item
- ✅ Subtotal calculated per item (price × quantity)
- ✅ Quantity can be updated from cart page
- ✅ Remove item button for each product
- ✅ Cart summary shows subtotal, estimated tax, shipping
- ✅ Total amount prominently displayed
- ✅ "Continue Shopping" button
- ✅ "Proceed to Checkout" button
- ✅ Empty cart shows message and "Shop Now" button

**Test Scenarios**:
1. View cart with items → All items displayed correctly
2. View empty cart → "Your cart is empty" message
3. Cart summary calculations → Accurate totals
4. Click product in cart → Navigate to product page
5. Cart persists across sessions (logged-in) → Items remain

---

### US-3.3: Update Cart Quantity

**As a** customer  
**I want to** change the quantity of items in my cart  
**So that** I can adjust my order before checkout

**Acceptance Criteria**:
- ✅ Quantity selector with +/- buttons
- ✅ Direct input for quantity
- ✅ Minimum quantity is 1
- ✅ Maximum quantity based on stock availability
- ✅ Cart totals update automatically
- ✅ Stock validation on quantity increase
- ✅ Warning if quantity exceeds stock
- ✅ Setting quantity to 0 removes item (with confirmation)

**Test Scenarios**:
1. Increase quantity → Cart total updates
2. Decrease quantity → Cart total updates
3. Set quantity beyond stock → Error: "Only X available"
4. Set quantity to 0 → Item removed from cart
5. Direct input invalid number → Resets to previous value

---

### US-3.4: Remove Item from Cart

**As a** customer  
**I want to** remove items from my cart  
**So that** I can delete products I no longer want

**Acceptance Criteria**:
- ✅ Remove button/icon for each cart item
- ✅ Confirmation prompt before removal
- ✅ Item removed immediately after confirmation
- ✅ Cart totals recalculated
- ✅ "Undo" option for 5 seconds after removal
- ✅ Success message displayed
- ✅ If last item removed, show empty cart message

**Test Scenarios**:
1. Click remove → Confirmation prompt appears
2. Confirm removal → Item removed, totals updated
3. Click undo within 5 seconds → Item restored
4. Remove last item → Empty cart message displayed

---

### US-3.5: Apply Coupon Code

**As a** customer  
**I want to** apply discount coupons to my order  
**So that** I can save money on my purchase

**Acceptance Criteria**:
- ✅ Coupon code input field in cart
- ✅ "Apply" button to validate and apply coupon
- ✅ Coupon validation (exists, not expired, usage limit)
- ✅ Minimum order amount validation
- ✅ Discount calculated and displayed in cart summary
- ✅ Only one coupon allowed per order
- ✅ Applied coupon shown with remove option
- ✅ Error messages for invalid coupons
- ✅ Coupon types: percentage off, fixed amount, free shipping

**Test Scenarios**:
1. Apply valid coupon → Discount applied, total updated
2. Apply expired coupon → Error: "Coupon expired"
3. Apply coupon below minimum order → Error: "Minimum order $X required"
4. Apply second coupon → Error: "Only one coupon allowed"
5. Remove applied coupon → Discount removed, total updated
6. Apply free shipping coupon → Shipping charge removed

---

### US-3.6: Wishlist Management

**As a** logged-in customer  
**I want to** save products to a wishlist  
**So that** I can purchase them later

**Acceptance Criteria**:
- ✅ Heart icon to add/remove from wishlist
- ✅ Icon fills when product is in wishlist
- ✅ Wishlist page shows all saved products
- ✅ "Move to Cart" button for each wishlist item
- ✅ Remove from wishlist option
- ✅ Wishlist item count badge
- ✅ Share wishlist via link
- ✅ Empty wishlist shows message
- ✅ Wishlist persists across devices (logged-in users)

**Test Scenarios**:
1. Click heart icon → Product added to wishlist
2. View wishlist page → All saved products displayed
3. Move item to cart → Item added to cart, removed from wishlist
4. Remove from wishlist → Item removed
5. Share wishlist → Shareable link generated
6. Login on different device → Wishlist synced

---

### US-3.7: Cart Persistence

**As a** customer  
**I want to** my cart to be saved  
**So that** I don't lose my selections if I leave the site

**Acceptance Criteria**:
- ✅ Guest cart saved in browser localStorage
- ✅ Logged-in cart saved in database/Redis
- ✅ Cart persists for 30 days (logged-in users)
- ✅ Guest cart merges with user cart on login
- ✅ Duplicate products have quantities combined
- ✅ Cart syncs across devices (logged-in users)
- ✅ Stock availability re-checked on cart load
- ✅ Out-of-stock items flagged in cart

**Test Scenarios**:
1. Add items as guest, close browser → Cart persists on return
2. Add items, login → Guest cart merged with user cart
3. Add items on mobile, login on desktop → Cart synced
4. Cart item out of stock → Flagged with message
5. Cart older than 30 days → Cleared automatically

---

## EPIC 4: Checkout & Payment

### US-4.1: Initiate Checkout

**As a** customer  
**I want to** proceed to checkout from my cart  
**So that** I can complete my purchase

**Acceptance Criteria**:
- ✅ "Proceed to Checkout" button in cart
- ✅ Stock validation before checkout
- ✅ Guest checkout option (email required)
- ✅ Login/register prompt for guests
- ✅ Multi-step checkout flow (Address → Delivery → Payment → Review)
- ✅ Progress indicator shows current step
- ✅ Can navigate back to previous steps
- ✅ Order summary visible throughout checkout

**Test Scenarios**:
1. Click checkout as logged-in user → Proceed to address step
2. Click checkout as guest → Prompted for email or login
3. Checkout with out-of-stock item → Error message
4. Navigate between steps → Progress saved
5. Order summary updates → Accurate totals displayed

---

### US-4.2: Select Delivery Address

**As a** customer  
**I want to** choose where my order should be delivered  
**So that** it arrives at the correct location

**Acceptance Criteria**:
- ✅ Display all saved addresses as selectable cards
- ✅ Default address pre-selected
- ✅ "Add New Address" option
- ✅ Inline address form for new address
- ✅ Address validation (required fields, postal code format)
- ✅ Selected address highlighted
- ✅ "Continue" button to proceed to next step
- ✅ Can edit existing addresses
- ✅ Guest users enter address directly

**Test Scenarios**:
1. Select saved address → Address selected, can continue
2. Add new address → Form displayed, address saved
3. Submit invalid address → Validation errors shown
4. Edit existing address → Changes saved
5. Guest user → Address form displayed

---

### US-4.3: Choose Delivery Time Slot

**As a** customer  
**I want to** select a delivery date and time  
**So that** I can receive my order when convenient

**Acceptance Criteria**:
- ✅ Date picker shows next 7 available days
- ✅ Time slots: Morning (8-12), Afternoon (12-4), Evening (4-8)
- ✅ Unavailable slots shown as disabled
- ✅ Delivery charges displayed per slot
- ✅ Express delivery option (extra charge)
- ✅ Selected slot highlighted
- ✅ Estimated delivery date shown
- ✅ "Continue" to proceed

**Test Scenarios**:
1. Select date and time slot → Slot selected, charge displayed
2. Select express delivery → Additional charge added
3. Select unavailable slot → Slot disabled, cannot select
4. Change slot → Delivery charge updates
5. Continue to payment → Slot saved

---

### US-4.4: Select Payment Method

**As a** customer  
**I want to** choose how to pay for my order  
**So that** I can complete the purchase

**Acceptance Criteria**:
- ✅ Payment options: Credit/Debit Card, UPI, Wallet, Cash on Delivery
- ✅ Card payment form (number, expiry, CVV)
- ✅ Save card option (tokenized)
- ✅ Saved cards displayed (last 4 digits)
- ✅ CVV required for saved cards
- ✅ UPI ID input field
- ✅ Wallet selection (PayPal, Google Pay, Apple Pay)
- ✅ COD option with extra charge
- ✅ Secure payment badges displayed
- ✅ Selected method highlighted

**Test Scenarios**:
1. Select card payment → Card form displayed
2. Enter card details → Validation performed
3. Save card → Card tokenized and saved
4. Select saved card → CVV prompt shown
5. Select UPI → UPI ID input shown
6. Select COD → COD charge added to total

---

### US-4.5: Review and Place Order

**As a** customer  
**I want to** review my complete order before confirming  
**So that** I can ensure everything is correct

**Acceptance Criteria**:
- ✅ Complete order summary displayed
- ✅ Items list with quantities and prices
- ✅ Delivery address shown
- ✅ Delivery slot shown
- ✅ Payment method shown
- ✅ Price breakdown (subtotal, tax, delivery, discount, total)
- ✅ Edit buttons for each section
- ✅ Terms and conditions checkbox
- ✅ "Place Order" button
- ✅ Loading state during order processing
- ✅ Cannot place order without accepting terms

**Test Scenarios**:
1. Review order → All details correct
2. Click edit address → Return to address step
3. Place order without terms → Error: "Accept terms"
4. Place order → Processing, then confirmation
5. Payment fails → Error message, retry option

---

### US-4.6: Process Payment

**As a** customer  
**I want to** my payment to be processed securely  
**So that** my order is confirmed

**Acceptance Criteria**:
- ✅ Payment gateway integration (Stripe/Razorpay)
- ✅ 3D Secure authentication for cards
- ✅ Payment processing indicator
- ✅ Payment success confirmation
- ✅ Payment failure handling with retry
- ✅ Order created only after successful payment
- ✅ Inventory deducted on payment success
- ✅ Payment receipt generated
- ✅ Refund processing for failed orders

**Test Scenarios**:
1. Card payment succeeds → Order confirmed
2. Card payment fails → Error, retry option
3. 3D Secure required → Authentication prompt
4. UPI payment → Redirect to UPI app
5. COD selected → Order confirmed without payment
6. Payment timeout → Order cancelled, stock restored

---

### US-4.7: Order Confirmation

**As a** customer  
**I want to** receive confirmation after placing an order  
**So that** I know my order was successful

**Acceptance Criteria**:
- ✅ Order confirmation page displayed
- ✅ Order ID prominently shown
- ✅ Success message with checkmark
- ✅ Order summary with all details
- ✅ Estimated delivery date
- ✅ "Download Invoice" button
- ✅ "Track Order" button
- ✅ "Continue Shopping" button
- ✅ Confirmation email sent
- ✅ Confirmation SMS sent
- ✅ Cart cleared after order

**Test Scenarios**:
1. Order placed successfully → Confirmation page shown
2. Order ID displayed → Unique order number
3. Download invoice → PDF generated
4. Track order → Redirected to tracking page
5. Email received → Confirmation email in inbox
6. SMS received → Confirmation SMS delivered

---

## EPIC 5: Order Management

### US-5.1: View Order History

**As a** logged-in customer  
**I want to** see all my past orders  
**So that** I can track my purchase history

**Acceptance Criteria**:
- ✅ List of all orders in reverse chronological order
- ✅ Order card shows: Order ID, date, total, status
- ✅ Status badges color-coded (Pending, Shipped, Delivered, Cancelled)
- ✅ Filter by status (All, Pending, Delivered, Cancelled, Returned)
- ✅ Search orders by order ID or product name
- ✅ Pagination (10 orders per page)
- ✅ "View Details" button for each order
- ✅ "Reorder" button for delivered orders
- ✅ Empty state for no orders

**Test Scenarios**:
1. View order history → All orders displayed
2. Filter by "Delivered" → Only delivered orders shown
3. Search by order ID → Matching order found
4. Click "View Details" → Order details page opens
5. Click "Reorder" → Items added to cart
6. New user with no orders → "No orders yet" message

---

### US-5.2: View Order Details

**As a** customer  
**I want to** see detailed information about a specific order  
**So that** I can review what I purchased

**Acceptance Criteria**:
- ✅ Order ID and date displayed
- ✅ Current order status with badge
- ✅ Status timeline (Placed → Confirmed → Packed → Shipped → Delivered)
- ✅ Items list with images, names, quantities, prices
- ✅ Delivery address
- ✅ Payment method
- ✅ Price breakdown (subtotal, tax, delivery, discount, total)
- ✅ "Download Invoice" button
- ✅ "Track Order" button (if shipped)
- ✅ "Cancel Order" button (if eligible)
- ✅ "Return Items" button (if eligible)

**Test Scenarios**:
1. View order details → All information displayed
2. Status timeline → Current status highlighted
3. Download invoice → PDF downloaded
4. Track order → Tracking page opens
5. Eligible for cancellation → Cancel button visible
6. Not eligible for cancellation → Cancel button hidden

---

### US-5.3: Track Order

**As a** customer  
**I want to** track my order's delivery status  
**So that** I know when to expect it

**Acceptance Criteria**:
- ✅ Visual status timeline
- ✅ Status updates: Placed, Confirmed, Packed, Shipped, Out for Delivery, Delivered
- ✅ Timestamp for each status
- ✅ Estimated delivery date
- ✅ Delivery partner name and tracking number
- ✅ "Refresh Status" button
- ✅ Real-time updates (if available)
- ✅ Delivery person contact (when out for delivery)
- ✅ Proof of delivery (photo/signature)

**Test Scenarios**:
1. Track shipped order → Status timeline displayed
2. Order out for delivery → Delivery person contact shown
3. Refresh status → Latest status fetched
4. Order delivered → Proof of delivery shown
5. Order in transit → Estimated delivery date shown

---

### US-5.4: Cancel Order

**As a** customer  
**I want to** cancel my order before it ships  
**So that** I can avoid receiving unwanted items

**Acceptance Criteria**:
- ✅ Cancel button visible only for "Placed" or "Confirmed" orders
- ✅ Cancellation reason dropdown (Changed mind, Found better price, etc.)
- ✅ Optional comments field
- ✅ Confirmation modal before cancellation
- ✅ Order status updated to "Cancelled"
- ✅ Refund initiated automatically
- ✅ Refund timeline displayed (5-7 business days)
- ✅ Cancellation email sent
- ✅ Inventory restored
- ✅ Cannot cancel after order is packed

**Test Scenarios**:
1. Cancel eligible order → Cancellation successful
2. Select reason and confirm → Order cancelled, refund initiated
3. Try to cancel packed order → Cancel button disabled
4. Cancellation email → Email received
5. Refund processed → Amount credited to original payment method

---

### US-5.5: Return Order

**As a** customer  
**I want to** return items from a delivered order  
**So that** I can get a refund for unsatisfactory products

**Acceptance Criteria**:
- ✅ Return option available for 7 days after delivery
- ✅ Select items to return (partial or full return)
- ✅ Return reason dropdown (Defective, Wrong item, Not as described, etc.)
- ✅ Upload photos (required for damaged/defective items)
- ✅ Comments field for additional details
- ✅ Return pickup date selection
- ✅ Return policy displayed
- ✅ Return request submitted
- ✅ Return status tracking
- ✅ Refund after return inspection

**Test Scenarios**:
1. Request return within 7 days → Return form displayed
2. Select items and reason → Return request submitted
3. Upload photos → Images attached to request
4. Schedule pickup → Pickup date confirmed
5. Return approved → Refund initiated
6. Return rejected → Reason provided, no refund

---

### US-5.6: Download Invoice

**As a** customer  
**I want to** download my order invoice  
**So that** I have a record of my purchase

**Acceptance Criteria**:
- ✅ "Download Invoice" button on order details page
- ✅ PDF invoice generated
- ✅ Invoice includes: Company details, invoice number, date
- ✅ Customer details and billing/shipping address
- ✅ Items table with quantities and prices
- ✅ Tax breakdown (CGST, SGST, IGST)
- ✅ Total amount
- ✅ Payment method
- ✅ "Email Invoice" option
- ✅ Invoice number format: INV-YYYY-MM-XXXXX

**Test Scenarios**:
1. Click download invoice → PDF downloaded
2. Open PDF → All details correct and formatted
3. Email invoice → Invoice sent to registered email
4. Invoice number → Unique and sequential

---

### US-5.7: Reorder

**As a** customer  
**I want to** quickly reorder items from a previous order  
**So that** I can save time on repeat purchases

**Acceptance Criteria**:
- ✅ "Reorder" button on order history and order details
- ✅ All items from order added to cart
- ✅ Current prices applied (may differ from original order)
- ✅ Stock availability checked
- ✅ Out-of-stock items flagged
- ✅ Success notification with cart summary
- ✅ Redirect to cart page
- ✅ Price difference notification if applicable

**Test Scenarios**:
1. Click reorder → All items added to cart
2. Reorder with out-of-stock item → Item flagged, others added
3. Prices changed → Notification of price difference
4. Redirected to cart → All items visible
5. Reorder from partial return → Only non-returned items added

---

## EPIC 6: Reviews & Ratings

### US-6.1: Write Product Review

**As a** customer who purchased a product  
**I want to** write a review and rating  
**So that** I can share my experience with other customers

**Acceptance Criteria**:
- ✅ Review option available only for purchased products
- ✅ Star rating selector (1-5 stars)
- ✅ Review title field (max 100 characters)
- ✅ Review text field (min 20, max 500 characters)
- ✅ Photo upload (max 5 images, 5MB each)
- ✅ Character counter for text field
- ✅ One review per product per user
- ✅ Can edit review within 48 hours
- ✅ "Verified Purchase" badge on review
- ✅ Review submitted for moderation

**Test Scenarios**:
1. Write review for purchased product → Review submitted
2. Try to review non-purchased product → Option not available
3. Submit review with < 20 characters → Error: "Minimum 20 characters"
4. Upload photos → Images attached to review
5. Edit review within 48 hours → Changes saved
6. Try to edit after 48 hours → Edit option disabled

---

### US-6.2: View Product Reviews

**As a** customer  
**I want to** read reviews from other customers  
**So that** I can make informed purchase decisions

**Acceptance Criteria**:
- ✅ Reviews displayed on product page
- ✅ Rating summary (average rating, total reviews)
- ✅ Rating distribution (5 stars: X%, 4 stars: Y%, etc.)
- ✅ Sort options: Most Recent, Highest Rating, Lowest Rating, Most Helpful
- ✅ Filter by rating (5 stars, 4 stars, 3 stars, etc.)
- ✅ Verified purchase badge
- ✅ Review date displayed
- ✅ Helpful votes count
- ✅ Review photos displayed
- ✅ Pagination (10 reviews per page)
- ✅ "No reviews yet" message for products without reviews

**Test Scenarios**:
1. View product with reviews → Reviews displayed
2. Sort by "Most Helpful" → Reviews reordered
3. Filter by 5 stars → Only 5-star reviews shown
4. Click review photo → Full-size image displayed
5. Product with no reviews → "No reviews yet" message

---

### US-6.3: Mark Review as Helpful

**As a** customer  
**I want to** mark reviews as helpful  
**So that** useful reviews are highlighted for others

**Acceptance Criteria**:
- ✅ "Was this helpful?" prompt on each review
- ✅ Yes/No buttons
- ✅ Helpful count displayed
- ✅ One vote per user per review
- ✅ Vote persists across sessions (logged-in users)
- ✅ Cannot vote on own reviews
- ✅ Visual indication of voted state
- ✅ Can change vote

**Test Scenarios**:
1. Click "Yes" on helpful → Vote recorded, count increases
2. Click "No" → Vote recorded
3. Try to vote again → Previous vote updated
4. Try to vote on own review → Buttons disabled
5. Logout and login → Vote persists

---

### US-6.4: Review Moderation (Admin)

**As an** admin  
**I want to** moderate product reviews  
**So that** inappropriate content is not displayed

**Acceptance Criteria**:
- ✅ Pending reviews queue in admin dashboard
- ✅ Review details displayed (rating, text, photos, user)
- ✅ Approve button
- ✅ Reject button with reason
- ✅ Flag inappropriate reviews
- ✅ Delete reviews
- ✅ Respond to reviews as admin
- ✅ Bulk approve/reject
- ✅ Email notification to user on approval/rejection

**Test Scenarios**:
1. View pending reviews → All pending reviews listed
2. Approve review → Review published on product page
3. Reject review → Review not published, user notified
4. Flag review → Review marked for further review
5. Admin response → Response displayed under review

---

## EPIC 7: Admin Dashboard

### US-7.1: View Dashboard Analytics

**As an** admin  
**I want to** see key business metrics at a glance  
**So that** I can monitor store performance

**Acceptance Criteria**:
- ✅ Total sales (today, this week, this month, this year)
- ✅ Total orders count with trend
- ✅ Total customers count with growth rate
- ✅ Revenue chart (line/bar graph)
- ✅ Recent orders list (last 10)
- ✅ Low stock alerts
- ✅ Top selling products (last 30 days)
- ✅ Customer growth chart
- ✅ Order status breakdown (pie chart)
- ✅ Date range selector for charts

**Test Scenarios**:
1. View dashboard → All metrics displayed
2. Select date range → Charts update
3. Low stock alerts → Products below threshold shown
4. Click recent order → Navigate to order details
5. Revenue chart → Accurate data visualization

---

### US-7.2: Manage Products

**As an** admin  
**I want to** create, edit, and delete products  
**So that** I can maintain the product catalog

**Acceptance Criteria**:
- ✅ Products list with search and filters
- ✅ Add new product button
- ✅ Product form: Name, SKU, description, price, category, brand, images, stock
- ✅ Multiple image upload with drag-and-drop
- ✅ Rich text editor for description
- ✅ Category and brand dropdowns
- ✅ Stock quantity field
- ✅ Active/Inactive toggle
- ✅ Save and publish
- ✅ Edit existing products
- ✅ Delete products (with confirmation)
- ✅ Bulk delete
- ✅ Import products from CSV
- ✅ Export products to CSV

**Test Scenarios**:
1. Add new product → Product created and listed
2. Upload images → Images uploaded and displayed
3. Edit product → Changes saved
4. Delete product → Confirmation, product removed
5. Bulk delete → Multiple products deleted
6. Import CSV → Products created from file

---

### US-7.3: Manage Orders

**As an** admin  
**I want to** view and manage customer orders  
**So that** I can fulfill them efficiently

**Acceptance Criteria**:
- ✅ Orders list with filters (status, date range)
- ✅ Search by order ID or customer name
- ✅ Order details view
- ✅ Update order status dropdown
- ✅ Status options: Confirmed, Packed, Shipped, Delivered
- ✅ Print packing slip
- ✅ Print invoice
- ✅ Add tracking number
- ✅ Bulk status update
- ✅ Export orders to CSV
- ✅ Order notes field

**Test Scenarios**:
1. View orders → All orders listed
2. Filter by "Pending" → Only pending orders shown
3. Update status to "Shipped" → Status updated, customer notified
4. Print packing slip → PDF generated
5. Add tracking number → Saved and visible to customer
6. Bulk update status → Multiple orders updated

---

### US-7.4: Manage Customers

**As an** admin  
**I want to** view and manage customer accounts  
**So that** I can provide support and handle issues

**Acceptance Criteria**:
- ✅ Customers list with search
- ✅ Customer details page
- ✅ Order history for customer
- ✅ Total spent and lifetime value
- ✅ Block/Unblock customer
- ✅ Reset customer password
- ✅ Add admin notes
- ✅ Export customer list
- ✅ Customer registration date
- ✅ Last login date

**Test Scenarios**:
1. View customers → All customers listed
2. Search by email → Customer found
3. View customer details → All info displayed
4. Block customer → Customer cannot login
5. View order history → All customer orders shown
6. Export customers → CSV downloaded

---

### US-7.5: Manage Inventory

**As an** admin  
**I want to** track and update product stock levels  
**So that** inventory is accurate

**Acceptance Criteria**:
- ✅ Inventory list with current stock levels
- ✅ Low stock threshold alerts (< 10 items)
- ✅ Update stock quantity
- ✅ Stock history log
- ✅ Bulk stock update
- ✅ Out of stock products highlighted
- ✅ Stock reports (by category, date range)
- ✅ Export inventory to CSV

**Test Scenarios**:
1. View inventory → All products with stock levels
2. Update stock → Quantity updated
3. Low stock alerts → Products below threshold flagged
4. View stock history → All changes logged
5. Bulk update → Multiple products updated
6. Export inventory → CSV downloaded

---

### US-7.6: Manage Coupons

**As an** admin  
**I want to** create and manage discount coupons  
**So that** I can run promotional campaigns

**Acceptance Criteria**:
- ✅ Coupons list
- ✅ Create coupon form
- ✅ Coupon code (unique, alphanumeric)
- ✅ Discount type: Percentage, Fixed Amount, Free Shipping
- ✅ Discount value
- ✅ Minimum order amount
- ✅ Maximum discount cap
- ✅ Valid from and valid until dates
- ✅ Usage limit (total and per user)
- ✅ Active/Inactive toggle
- ✅ Edit and delete coupons
- ✅ Coupon usage statistics

**Test Scenarios**:
1. Create coupon → Coupon saved and listed
2. Set expiry date → Coupon expires automatically
3. Usage limit reached → Coupon becomes invalid
4. View usage stats → Accurate usage data
5. Deactivate coupon → Coupon cannot be used
6. Delete coupon → Coupon removed

---

### US-7.7: View Reports

**As an** admin  
**I want to** generate business reports  
**So that** I can analyze performance and make decisions

**Acceptance Criteria**:
- ✅ Sales report (daily, weekly, monthly, yearly)
- ✅ Product performance report
- ✅ Customer report (new, returning, lifetime value)
- ✅ Revenue analytics
- ✅ Category performance
- ✅ Date range selector
- ✅ Visual charts and graphs
- ✅ Export to PDF
- ✅ Export to CSV
- ✅ Export to Excel
- ✅ Scheduled reports (email daily/weekly)

**Test Scenarios**:
1. Generate sales report → Report displayed with charts
2. Select date range → Report updates
3. Export to PDF → PDF downloaded
4. Product performance → Top and bottom products shown
5. Schedule weekly report → Report emailed every week

---

### US-7.8: Configure Settings

**As an** admin  
**I want to** configure system settings  
**So that** the store operates according to business requirements

**Acceptance Criteria**:
- ✅ General settings (store name, logo, contact info)
- ✅ Payment gateway configuration (API keys)
- ✅ Email settings (SMTP server, from address)
- ✅ SMS settings (Twilio credentials)
- ✅ Tax settings (rates by region)
- ✅ Shipping zones and rates
- ✅ Currency settings
- ✅ Test email/SMS buttons
- ✅ Save settings button
- ✅ Settings validation

**Test Scenarios**:
1. Update store name → Name updated across site
2. Configure payment gateway → API keys saved securely
3. Test email → Test email sent successfully
4. Configure tax rates → Taxes calculated correctly
5. Set shipping rates → Rates applied at checkout

---

## EPIC 8: Notifications & Communication

### US-8.1: Receive Email Notifications

**As a** customer  
**I want to** receive email notifications for important events  
**So that** I stay informed about my orders

**Acceptance Criteria**:
- ✅ Welcome email on registration
- ✅ Email verification email
- ✅ Password reset email
- ✅ Order confirmation email
- ✅ Order shipped email with tracking
- ✅ Order delivered email
- ✅ Return/refund confirmation email
- ✅ Promotional emails (if opted in)
- ✅ Newsletter (if subscribed)
- ✅ Emails are mobile-responsive
- ✅ Unsubscribe link in promotional emails

**Test Scenarios**:
1. Register account → Welcome email received
2. Place order → Order confirmation email received
3. Order shipped → Shipping email with tracking link
4. Unsubscribe from promotions → No more promotional emails
5. Email opens on mobile → Properly formatted

---

### US-8.2: Receive SMS Notifications

**As a** customer  
**I want to** receive SMS alerts for critical updates  
**So that** I'm immediately notified about my orders

**Acceptance Criteria**:
- ✅ OTP for phone verification
- ✅ Order confirmation SMS
- ✅ Order shipped SMS
- ✅ Out for delivery SMS
- ✅ Order delivered SMS
- ✅ SMS preferences in settings
- ✅ Opt-out option
- ✅ SMS includes order ID and tracking link

**Test Scenarios**:
1. Place order → Confirmation SMS received
2. Order out for delivery → SMS alert received
3. Opt-out of SMS → No more SMS notifications
4. OTP verification → OTP SMS received within 30 seconds

---

### US-8.3: Receive Push Notifications

**As a** customer  
**I want to** receive browser/app push notifications  
**So that** I get real-time updates

**Acceptance Criteria**:
- ✅ Permission prompt on first visit
- ✅ Order status updates
- ✅ Promotional offers
- ✅ Price drop alerts (wishlist items)
- ✅ Back in stock notifications
- ✅ Abandoned cart reminders
- ✅ Notification bell icon with badge
- ✅ Notification center dropdown
- ✅ Mark as read
- ✅ Notification preferences

**Test Scenarios**:
1. Allow notifications → Permission granted
2. Order status changes → Push notification received
3. Wishlist item price drops → Notification received
4. Click notification → Navigate to relevant page
5. Disable notifications → No more push notifications

---

### US-8.4: Manage Notification Preferences

**As a** customer  
**I want to** control which notifications I receive  
**So that** I only get relevant communications

**Acceptance Criteria**:
- ✅ Notification preferences page
- ✅ Email toggles (Orders, Promotions, Newsletter)
- ✅ SMS toggles (Orders, Delivery updates)
- ✅ Push notification toggles (Orders, Offers, Alerts)
- ✅ "Unsubscribe from all" option
- ✅ Save preferences button
- ✅ Preferences apply immediately
- ✅ Cannot disable critical notifications (order confirmations)

**Test Scenarios**:
1. Disable promotional emails → No promotional emails received
2. Enable SMS delivery updates → SMS received for deliveries
3. Unsubscribe from all → Only critical notifications received
4. Save preferences → Settings persisted
5. Try to disable order confirmations → Option disabled/grayed out

---

### US-8.5: View In-App Notifications

**As a** logged-in customer  
**I want to** see notifications within the application  
**So that** I don't miss important updates

**Acceptance Criteria**:
- ✅ Notification bell icon in header
- ✅ Unread count badge
- ✅ Notification dropdown on click
- ✅ List of recent notifications (last 30)
- ✅ Notification types: Order updates, Promotions, Alerts
- ✅ Mark individual notification as read
- ✅ "Mark all as read" button
- ✅ Delete notification option
- ✅ Click notification → Navigate to relevant page
- ✅ Real-time updates (WebSocket/polling)

**Test Scenarios**:
1. New notification → Badge count increases
2. Click bell icon → Dropdown shows notifications
3. Mark as read → Notification marked, badge decreases
4. Mark all as read → All notifications marked
5. Delete notification → Notification removed
6. Click notification → Navigate to order/product page

---

## EPIC 9: Advanced Watchlist Management

### US-9.1: Save Product Variant to Watchlist

**As a** logged-in customer  
**I want to** save specific product variants to my watchlist  
**So that** I can track prices for the exact variant I'm interested in

**Acceptance Criteria**:
- ✅ User can add product variant to watchlist from product detail page
- ✅ Variant selection (size, weight, etc.) is captured when adding to wishlist
- ✅ Heart icon reflects whether current variant is in wishlist
- ✅ Price at time of adding is recorded (`price_at_watch`)
- ✅ User can have multiple variants of same product in wishlist
- ✅ Wishlist syncs across devices for logged-in users
- ✅ Variant details displayed in wishlist (e.g., "Organic Milk - 500g")
- ✅ Remove specific variant from wishlist
- ✅ Wishlist count badge shows total items (including variants)

**Test Scenarios**:
1. Select "500g" variant, click heart → Variant added to wishlist
2. Change to "1kg" variant, click heart → Both variants in wishlist
3. View wishlist → See "Organic Milk - 500g" and "Organic Milk - 1kg" as separate items
4. Remove "500g" variant → Only "1kg" remains in wishlist
5. Login on different device → Wishlist synced with both variants
6. Add base product (no variant) → Saved separately from variants

---

### US-9.2: View Price Changes in Watchlist

**As a** customer with items in my watchlist  
**I want to** see when prices have dropped  
**So that** I can buy products when they're cheaper

**Acceptance Criteria**:
- ✅ Watchlist displays price at which item was added
- ✅ Current price shown next to original price
- ✅ Price drop highlighted in green with percentage
- ✅ Price increase shown in red (optional)
- ✅ "Price Drop" badge for items with decreased prices
- ✅ Filter option to show only items with price drops
- ✅ Price trend icon (↓ for decrease, ↑ for increase, → for same)
- ✅ Minimum threshold for price drop ($0.50 or configurable)
- ✅ Pull-to-refresh updates prices in real-time

**Test Scenarios**:
1. Add item at $29.99 → Price recorded as $29.99
2. Admin changes price to $24.99 → Watchlist shows "Was $29.99, Now $24.99"
3. Price drop indicator → Green badge with "-17%"
4. Filter by "Price Drops" → Only items with price decreases shown
5. Price increases to $34.99 → Red indicator (optional feature)
6. Price stays same → No badge, neutral icon
7. Pull to refresh → Prices updated from database

---

### US-9.3: Instant Wishlist State with Redis

**As a** customer browsing products  
**I want to** see wishlist status instantly  
**So that** I know which items I've already saved

**Acceptance Criteria**:
- ✅ Heart icon state loads instantly (< 50ms) on product pages
- ✅ Wishlist state cached in Redis for fast lookups
- ✅ Adding to wishlist updates both Redis and database
- ✅ Removing from wishlist updates both Redis and database
- ✅ Redis cache syncs with database on user login
- ✅ Cache expires after 7 days of inactivity
- ✅ Fallback to database if Redis unavailable
- ✅ Manual sync option in settings
- ✅ No duplicate entries in cache

**Test Scenarios**:
1. Login → Wishlist loaded from DB to Redis
2. Browse product page → Heart icon state shown instantly (Redis lookup)
3. Add to wishlist → Redis and PostgreSQL both updated
4. Check Redis → Key `watchlist:{userId}` contains item
5. Logout and login → Wishlist state persists
6. Redis server down → Fallback to database, slower but functional
7. Manual sync → Redis cache refreshed from database
8. 7 days of inactivity → Cache expires, reloaded on next login

---

## EPIC 10: Location-Based Branch Routing

### US-10.1: Select Delivery Address to Resolve Branch

**As a** logged-in customer opening the app  
**I want to** select one of my saved delivery addresses before reaching the Home Page  
**So that** I see products, pricing, and promotions relevant to the branch that serves my area

**Acceptance Criteria**:
- ✅ If no active branch context exists in session, user is redirected to Address Selection screen before Home Page
- ✅ Address Selection screen displays all saved delivery addresses as selectable cards
- ✅ Default address is pre-selected (if one exists)
- ✅ User can add a new address inline if no addresses are saved
- ✅ On address selection, the backend extracts the `post_office` field and resolves it to a `branch_id`
- ✅ Resolved `branch_id` is stored in the user's Redis session for 30 days
- ✅ User is redirected to the Home Page filtered by the resolved branch
- ✅ If the Post Office is not served by any branch, a clear "We don't serve this area yet" message is shown
- ✅ Current branch name is displayed in the Home Page header
- ✅ User can change branch at any time via "Change Location" in the header

**Test Scenarios**:
1. Open app with no branch context → Redirected to Address Selection screen
2. Select saved address (served area) → Branch resolved, redirected to Home Page
3. Select saved address (unserved area) → Error: "We don't serve this area yet"
4. Open app with active branch context → Go directly to Home Page
5. Tap "Change Location" on Home Page → Return to Address Selection
6. Add new address during selection → Address saved, then branch resolved
7. Session expires after 30 days → Address Selection triggered again on next app open

---

### US-10.2: View Quick Sale Items on Home Page

**As a** customer with an active branch context  
**I want to** see the highest-discount products on the Home Page  
**So that** I can quickly find the best deals available in my area

**Acceptance Criteria**:
- ✅ Home Page displays only "Quick Sale" items — products with the highest discount percentages for the active branch
- ✅ Discount percentage is calculated as: `(compare_at_price - price) / compare_at_price * 100`
- ✅ Only products with `compare_at_price > price` and in-stock at the branch are shown
- ✅ Default display: 20 items sorted by highest discount percentage
- ✅ Each product card shows: image, name, sale price, original price (strikethrough), discount percentage badge
- ✅ Pull-to-refresh updates the Quick Sale feed
- ✅ Infinite scroll or "Load More" for additional items
- ✅ General product browsing is available via Category screens (not on Home Page)
- ✅ If no Quick Sale items are available, an empty state is shown with a "Browse Categories" link
- ✅ Branch name displayed at the top of the Home Page

**Test Scenarios**:
1. View Home Page with active branch → Quick Sale items displayed, sorted by discount
2. Product with 40% discount appears above product with 20% discount → Correct sort order
3. Product out of stock at branch → Not shown in Quick Sale even if discounted
4. No discounted products in branch → Empty state with "Browse Categories" button
5. Pull to refresh → Quick Sale items reloaded from server
6. Tap product card → Navigate to Product Detail page
7. Product's discount removed by Marketing Manager → Product disappears from Quick Sale on next refresh
8. Switch branch via "Change Location" → Home Page refreshes with new branch's Quick Sale items

---

### US-10.3: Manage Product Discounts (Marketing Manager)

**As a** Marketing Manager assigned to a branch  
**I want to** set and update discounts on products in my branch  
**So that** the best deals automatically appear on customers' Home Page Quick Sale feed

**Acceptance Criteria**:
- ✅ Marketing Manager can view all products stocked in their assigned branch
- ✅ Can set `price` (sale price) and `compare_at_price` (original price) for each product
- ✅ Discount percentage is auto-calculated and displayed in real-time: `(compare_at_price - price) / compare_at_price * 100`
- ✅ Can only modify products that have inventory in their branch
- ✅ Cannot modify products in other branches
- ✅ Saving a discount auto-populates the Quick Sale feed (highest discounts float to the top)
- ✅ All discount changes are audit-logged in `admin_audit_logs`
- ✅ Can preview the current Quick Sale feed as customers would see it
- ✅ Bulk discount update supported (e.g., apply 15% off to a category)
- ✅ Discount Performance analytics dashboard available (views, conversions, revenue impact)
- ✅ `compare_at_price` must be greater than `price` (validated server-side)
- ✅ Cannot manage inventory, users, orders, or system settings

**Test Scenarios**:
1. Login as Marketing Manager → Dashboard shows discount management for assigned branch only
2. Set product price to 999, compare_at_price to 1500 → Discount shows as 33.4%
3. Save discount → Product appears in Quick Sale feed (customer-facing)
4. Try to modify product in another branch → Access denied
5. Remove discount (set compare_at_price = null) → Product removed from Quick Sale
6. View Quick Sale Preview → Shows top 20 discounted products as customers see them
7. Bulk update: Apply 10% discount to "Groceries" category → All matching products updated
8. View Discount Performance → Charts show click-through, conversion, and revenue data
9. Check audit logs → All discount changes recorded with old/new values

---

### US-10.4: Manage Post Office to Branch Mappings (Super Admin)

**As a** Super Admin  
**I want to** manage which Post Offices are served by which branches  
**So that** customer addresses are correctly routed to the nearest/serving branch

**Acceptance Criteria**:
- ✅ Super Admin can view all Post Office → Branch mappings in a table
- ✅ Can create new mappings (Post Office name → Branch)
- ✅ Each Post Office maps to exactly one branch (unique constraint)
- ✅ Can update the branch assigned to a Post Office
- ✅ Can deactivate a mapping (customers with that Post Office will see "area not served")
- ✅ Can delete mappings (with confirmation)
- ✅ Can bulk-import mappings via CSV (columns: post_office, branch_code, district, province)
- ✅ Search by Post Office name
- ✅ Filter by branch, district, or province
- ✅ Validation: Post Office name is unique, Branch must exist and be active
- ✅ Changes take effect immediately for new branch resolutions (existing sessions are unaffected until refresh)

**Test Scenarios**:
1. View mappings → All Post Office → Branch entries listed
2. Add new mapping: "Nugegoda" → "Colombo Branch" → Mapping saved
3. Try duplicate Post Office → Error: "Nugegoda is already mapped"
4. Deactivate mapping → Customers with that Post Office see "area not served"
5. Bulk import 50 mappings via CSV → All imported, duplicates reported as errors
6. Update mapping: "Nugegoda" from "Colombo Branch" to "Kandy Branch" → Updated
7. Delete mapping → Confirmation modal, then removed
8. Customer selects address in mapped area → Branch resolved successfully
9. Customer selects address in unmapped area → "We don't serve this area" error

---

## 📊 User Stories Summary

| EPIC | User Stories Count |
|------|-------------------|
| EPIC 1: Authentication | 7 |
| EPIC 2: Product Catalog | 6 |
| EPIC 3: Shopping Cart | 7 |
| EPIC 4: Checkout & Payment | 7 |
| EPIC 5: Order Management | 7 |
| EPIC 6: Reviews & Ratings | 4 |
| EPIC 7: Admin Dashboard | 8 |
| EPIC 8: Notifications | 5 |
| EPIC 9: Advanced Watchlist | 3 |
| EPIC 10: Location-Based Branch Routing | 4 |

**Total User Stories**: 58


---

## 📝 User Story Template

For creating additional user stories, use this format:

```
**As a** [role]  
**I want to** [action/feature]  
**So that** [benefit/value]

**Acceptance Criteria**:
- ✅ Criterion 1
- ✅ Criterion 2
- ✅ Criterion 3

**Test Scenarios**:
1. Scenario 1 → Expected result
2. Scenario 2 → Expected result
```

---

*Document Version: 3.0*  
*Last Updated: February 17, 2026*  
*Total User Stories: 58*
